"""Analysis lifecycle routes."""

from fastapi import APIRouter, Depends, Query, Request, Response
from app.api.dependencies import get_service
from app.api.schemas import AnalyzeRequestModel, AnalyzeResponse

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse, status_code=202)
def analyze(body: AnalyzeRequestModel, request: Request, response: Response, service=Depends(get_service)):
    ticket = service.request_analysis(body, request.client.host if request.client else "unknown", body.force)
    if ticket.cached:
        response.status_code = 200
    return AnalyzeResponse(
        analysis_id=ticket.analysis_id, status=ticket.status, cached=ticket.cached,
        deduplicated=ticket.deduplicated, status_url=f"/analyses/{ticket.analysis_id}",
        results_url=f"/scores/{ticket.analysis_id}",
    )


@router.get("/analyses/{analysis_id}")
def analysis_status(analysis_id: str, service=Depends(get_service)):
    item = service.get_analysis(analysis_id)
    return {
        "analysis_id": item.id, "status": item.status, "stage": item.stage,
        "progress": item.progress, "message": item.message, "head_sha": item.head_sha,
        "params": item.params, "error": {"code": item.error_code, "message": item.error_message} if item.error_code else None,
        "cached_from": item.cached_from, "commit_count": item.commit_count,
        "created_at": item.created_at, "started_at": item.started_at, "finished_at": item.finished_at,
    }


@router.get("/analyses")
def analyses(limit: int = Query(20, ge=1, le=50), offset: int = Query(0, ge=0), service=Depends(get_service)):
    session = service.session_factory()
    try:
        from app.db import crud
        return {"analyses": [
            {"analysis_id": item.id, "status": item.status, "progress": item.progress,
             "created_at": item.created_at, "finished_at": item.finished_at}
            for item in crud.list_analyses(session, min(limit, 50), max(offset, 0))
        ]}
    finally:
        session.close()


@router.get("/repos/{owner}/{repo}/latest")
def latest(owner: str, repo: str, service=Depends(get_service)):
    session = service.session_factory()
    try:
        from app.db.models import Repository
        from app.db import crud
        repository = session.query(Repository).filter_by(full_name=f"{owner}/{repo}".lower()).first()
        item = crud.latest_succeeded_for_repo(session, repository.id) if repository else None
        if not item:
            from app.core.errors import AnalysisNotFound
            raise AnalysisNotFound("No succeeded analysis found")
        return {"analysis_id": item.id, "finished_at": item.finished_at, "head_sha": item.head_sha}
    finally:
        session.close()
