"""Analysis request service tests."""

from datetime import datetime, timedelta, timezone

import pytest

from app.api.schemas import AnalyzeRequestModel
from app.core.errors import QueueFull, TooManyRequests
from app.db.base import create_engine_from_url, init_db, make_session_factory
from app.db import crud
from app.services.analysis_service import AnalysisService


class Runner:
    def __init__(self):
        self.submitted = []

    def submit(self, analysis_id, request):
        self.submitted.append((analysis_id, request))


class Limiter:
    def __init__(self, allowed=True):
        self.allowed = allowed

    def allow(self, _):
        return self.allowed


def _service(tmp_path, runner=None, clock=None):
    engine = create_engine_from_url(f"sqlite:///{tmp_path / 'service.db'}")
    init_db(engine)
    factory = make_session_factory(engine)
    runner = runner or Runner()
    service = AnalysisService(
        factory,
        runner,
        Limiter(),
        clock=clock or (lambda: datetime.now(timezone.utc)),
        remote_head_fn=lambda _: "a" * 40,
        meta_fn=lambda owner, repo: {
            "clone_url": f"https://github.com/{owner}/{repo}.git",
            "default_branch": "main",
            "full_name": f"{owner}/{repo}",
        },
    )
    return service, factory, runner, engine


def test_request_deduplicates_and_cache_hits(tmp_path):
    service, factory, runner, engine = _service(tmp_path)
    raw = AnalyzeRequestModel(repo_url="https://github.com/owner/repo", max_commits=10)
    first = service.request_analysis(raw, "127.0.0.1")
    second = service.request_analysis(raw, "127.0.0.1")
    assert first.analysis_id == second.analysis_id
    assert second.deduplicated
    with factory() as session:
        analysis = crud.get_analysis(session, first.analysis_id)
        crud.mark_succeeded(session, analysis.id, {}, 0, analysis.head_sha)
    third = service.request_analysis(raw, "127.0.0.1")
    assert third.cached
    assert third.analysis_id == first.analysis_id
    assert len(runner.submitted) == 1
    assert runner.submitted[0][1].github_repo == "owner/repo"
    engine.dispose()


def test_force_creates_new_analysis_and_rate_limit_is_enforced(tmp_path):
    service, _, runner, engine = _service(tmp_path)
    raw = AnalyzeRequestModel(repo_url="owner/repo")
    first = service.request_analysis(raw, "client")
    with service.session_factory() as session:
        analysis = crud.get_analysis(session, first.analysis_id)
        crud.mark_succeeded(session, analysis.id, {}, 0, analysis.head_sha)
    forced = service.request_analysis(raw.model_copy(update={"force": True}), "client")
    assert forced.analysis_id != first.analysis_id
    assert len(runner.submitted) == 2
    service.limiter = Limiter(False)
    with pytest.raises(TooManyRequests):
        service.request_analysis(raw, "client")
    engine.dispose()


def test_queue_full_is_rejected(tmp_path, monkeypatch):
    service, factory, _, engine = _service(tmp_path)
    monkeypatch.setattr("app.services.analysis_service.settings.MAX_QUEUED_ANALYSES", 0)
    with pytest.raises(QueueFull):
        service.request_analysis(AnalyzeRequestModel(repo_url="owner/repo"), "client")
    engine.dispose()
