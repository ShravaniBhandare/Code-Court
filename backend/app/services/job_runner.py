"""Background analysis execution."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import logging
import time

from app.config import settings
from app.core.errors import (
    AnalysisTimeout, CloneFailed, GitHubAPIError, InvalidRepoURL, RateLimited,
    RepoNotFound, RepoTooLarge, AnalysisCancelled,
)
from app.core.pipeline import AnalysisRequest, PipelineOutput, run_pipeline
from app.db import crud

logger = logging.getLogger(__name__)


class JobRunner:
    """Runs analyses with isolated sessions."""

    def __init__(self, session_factory, pipeline_fn=run_pipeline, max_workers=settings.MAX_CONCURRENT_ANALYSES, synchronous: bool = False, clock=time.monotonic):
        self.session_factory = session_factory
        self.pipeline_fn = pipeline_fn
        self.clock = clock
        self.synchronous = synchronous
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def submit(self, analysis_id: str, request: AnalysisRequest) -> None:
        if self.synchronous:
            self._run(analysis_id, request)
        else:
            self.executor.submit(self._run, analysis_id, request)

    def _run(self, analysis_id: str, request: AnalysisRequest) -> None:
        session = self.session_factory()
        try:
            crud.mark_running(session, analysis_id)
            started = self.clock()
            last_write = [0.0]
            last_stage = [""]
            def progress(stage: str, fraction: float, message: str) -> None:
                if self.clock() - last_write[0] >= 1 or stage != last_stage[0] or fraction >= 1:
                    crud.update_progress(session, analysis_id, stage, fraction, message)
                    last_write[0] = self.clock()
                    last_stage[0] = stage
            def should_stop() -> None:
                if self.clock() - started >= settings.ANALYSIS_TIMEOUT_SEC:
                    raise AnalysisTimeout("Analysis timed out")
            output = self.pipeline_fn(request, progress=progress, should_stop=should_stop)
            crud.save_results(session, analysis_id, [
                {"author_key": item.author_key, "display_name": item.display_name, "display_email": item.display_email, "rank": item.rank, "score": item.score, "base_score": item.base_score, "share_of_team": item.share_of_team, "penalty_multiplier": item.penalty_multiplier, "commits": item.commits, "credited_lines": item.credited_lines, "surviving_lines": item.surviving_lines, "signals": {key: value.__dict__ for key, value in item.signals.items()}, "notes": list(item.notes)}
                for item in output.report.authors
            ], [
                {"author_key": item.author_key, "display_name": item.display_name, "kind": item.kind, "severity": item.severity, "message": item.message, "evidence": item.evidence, "penalty_multiplier": item.penalty_multiplier}
                for item in output.anomalies
            ], output.commit_rows)
            crud.mark_succeeded(session, analysis_id, output.report_dict, len(output.commit_rows), output.head_sha)
        except BaseException as error:
            code, message = _failure(error)
            try:
                session.rollback()
                crud.mark_failed(session, analysis_id, code, message)
            except Exception:
                logger.exception("Unable to persist analysis failure")
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                raise
        finally:
            session.close()

    def startup_recovery(self) -> None:
        session = self.session_factory()
        try:
            crud.fail_stale_analyses(session, "Server restarted while the analysis was running")
        finally:
            session.close()

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)


def _failure(error: BaseException) -> tuple[str, str]:
    if isinstance(error, InvalidRepoURL):
        return "invalid_url", str(error)
    if isinstance(error, RepoNotFound):
        return "repo_not_found", str(error)
    if isinstance(error, RepoTooLarge):
        return "repo_too_large", str(error)
    if isinstance(error, RateLimited):
        return "github_rate_limited", str(error)
    if isinstance(error, GitHubAPIError):
        return "github_error", str(error)
    if isinstance(error, CloneFailed):
        return "clone_failed", str(error)
    if isinstance(error, AnalysisTimeout):
        return "timeout", "Analysis timed out"
    if isinstance(error, AnalysisCancelled):
        return "cancelled", "Analysis cancelled"
    logger.exception("Analysis failed unexpectedly", exc_info=error)
    return "internal_error", "Analysis failed unexpectedly"
