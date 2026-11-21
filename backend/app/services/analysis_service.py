"""Analysis request orchestration and result queries."""

from datetime import datetime, timedelta, timezone
from threading import Lock
from pathlib import Path

from app.config import settings
from app.core.cloner import get_remote_head_sha
from app.core.errors import AnalysisNotFound, AnalysisNotReady, QueueFull, TooManyRequests
from app.core.github_meta import fetch_repo_meta
from app.core.pipeline import AnalysisRequest, params_hash, run_pipeline
from app.core.repo_url import parse_repo_url
from app.core.scoring_config import make_config
from app.db import crud


class AnalysisService:
    def __init__(self, session_factory, runner, limiter, clock=lambda: datetime.now(timezone.utc), remote_head_fn=get_remote_head_sha, meta_fn=fetch_repo_meta):
        self.session_factory = session_factory
        self.runner = runner
        self.limiter = limiter
        self.clock = clock
        self.remote_head_fn = remote_head_fn
        self.meta_fn = meta_fn
        self._lock = Lock()

    def request_analysis(self, raw, client_ip: str, force: bool = False):
        force = force or bool(getattr(raw, "force", False))
        if not self.limiter.allow(client_ip):
            raise TooManyRequests("Analysis request limit exceeded")
        owner, repo = parse_repo_url(raw.repo_url)
        config = make_config(raw.weights, raw.scaling or "log")
        max_commits = min(settings.API_MAX_COMMITS, max(1, raw.max_commits or settings.DEFAULT_MAX_COMMITS))
        meta = self.meta_fn(owner, repo)
        head = self.remote_head_fn(meta["clone_url"])
        request = AnalysisRequest(
            f"{owner}/{repo}",
            max_commits=max_commits,
            since=_day_datetime(raw.since),
            until=_day_datetime(raw.until),
            scaling=config.scaling,
            weights=config.weights,
            use_github=raw.use_github,
            enable_penalties=raw.enable_penalties,
            github_repo=f"{owner}/{repo}" if raw.use_github else None,
            deadline=_deadline(raw.deadline),
        )
        normalized = __import__("app.core.pipeline", fromlist=["normalized_params"]).normalized_params(request)
        digest = params_hash(request)
        with self._lock:
            session = self.session_factory()
            try:
                repository = crud.get_or_create_repository(session, owner, repo, meta.get("default_branch", "main"))
                if not force:
                    cached = crud.find_cached_analysis(session, repository.id, head, digest, settings.PIPELINE_VERSION, self.clock() - timedelta(hours=settings.ANALYSIS_TTL_HOURS))
                    if cached:
                        session.commit()
                        return _ticket(cached.id, cached.status, True, False)
                inflight = crud.find_inflight_analysis(session, repository.id, digest, settings.PIPELINE_VERSION)
                if inflight:
                    session.commit()
                    return _ticket(inflight.id, inflight.status, False, True)
                if crud.count_queued(session) >= settings.MAX_QUEUED_ANALYSES:
                    raise QueueFull("Analysis queue is full")
                analysis = crud.create_analysis(session, repository.id, head, normalized, digest, settings.PIPELINE_VERSION)
                session.commit()
                ticket = _ticket(analysis.id, "queued", False, False)
            finally:
                session.close()
        self.runner.submit(ticket.analysis_id, request)
        return ticket

    def get_analysis(self, analysis_id: str):
        session = self.session_factory()
        try:
            analysis = crud.get_analysis(session, analysis_id)
            if not analysis:
                raise AnalysisNotFound("Analysis not found")
            return analysis
        finally:
            session.close()

    def get_scores(self, analysis_id: str):
        analysis = self.get_analysis(analysis_id)
        if analysis.status != "succeeded":
            raise AnalysisNotReady(f"Analysis is {analysis.status}")
        session = self.session_factory()
        try:
            return analysis, crud.get_scores(session, analysis_id)
        finally:
            session.close()


class AnalysisTicket:
    def __init__(self, analysis_id, status, cached, deduplicated):
        self.analysis_id = analysis_id
        self.status = status
        self.cached = cached
        self.deduplicated = deduplicated


def _ticket(*args):
    return AnalysisTicket(*args)


def _deadline(value):
    if value is None:
        return None
    return datetime.combine(value, datetime.max.time(), tzinfo=timezone.utc)


def _day_datetime(value):
    if value is None:
        return None
    return datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc)
