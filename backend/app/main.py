"""FastAPI application entry point."""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.errors import (
    AnalysisNotFound, AnalysisNotReady, CloneFailed, GitHubAPIError,
    InvalidRepoURL, QueueFull, RateLimited, RepoNotFound, RepoTooLarge,
    TooManyRequests,
)
from app.config import settings
from app.db.base import create_engine_from_url, init_db, make_session_factory
from app.services.job_runner import JobRunner
from app.services.analysis_service import AnalysisService
from app.services.rate_limit import SlidingWindowLimiter
from app.api.routes_analysis import router as analysis_router
from app.api.routes_results import router as results_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    engine = create_engine_from_url(settings.DATABASE_URL)
    init_db(engine)
    factory = make_session_factory(engine)
    runner = JobRunner(factory)
    runner.startup_recovery()
    application.state.analysis_service = AnalysisService(
        factory, runner, SlidingWindowLimiter(settings.MAX_ANALYZE_PER_MINUTE_PER_IP, 60)
    )
    try:
        yield
    finally:
        runner.shutdown()
        engine.dispose()


app = FastAPI(title="CodeCourt API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(analysis_router)
app.include_router(results_router)


@app.get("/", include_in_schema=False)
def root_redirect():
    return RedirectResponse(url="/docs", status_code=307)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exception: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": {"code": "validation_error", "message": "Invalid request", "details": exception.errors()}})


def _handler(status: int, code: str):
    async def handle(_: Request, exception: Exception):
        headers = {"Retry-After": "60"} if status == 429 else None
        response = JSONResponse(status_code=status, content={"error": {"code": code, "message": str(exception)}}, headers=headers)
        return response
    return handle


for _exception, _status, _code in (
    (InvalidRepoURL, 422, "invalid_url"), (RepoNotFound, 404, "repo_not_found"),
    (AnalysisNotFound, 404, "analysis_not_found"), (AnalysisNotReady, 409, "analysis_not_ready"),
    (RepoTooLarge, 413, "repo_too_large"), (TooManyRequests, 429, "too_many_requests"),
    (RateLimited, 429, "github_rate_limited"), (QueueFull, 503, "queue_full"),
    (GitHubAPIError, 502, "github_error"), (CloneFailed, 502, "clone_failed"),
):
    app.add_exception_handler(_exception, _handler(_status, _code))


@app.exception_handler(Exception)
async def internal_error(_: Request, exception: Exception):
    logger.exception("Unhandled API exception", exc_info=exception)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "Internal server error"}},
    )


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return the service health status."""
    return {"status": "ok", "service": "codecourt"}
