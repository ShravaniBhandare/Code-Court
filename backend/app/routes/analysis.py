from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.repository import Repository
from app.schemas.analysis import AnalysisResponse
from app.services.analysis_service import AnalysisService
from app.utils.session import get_session_data


router = APIRouter(prefix="/api/repositories", tags=["analysis"])


@router.get(
    "/{repository_id}/analysis",
    response_model=AnalysisResponse,
)
async def analyze_repository(
    repository_id: int,
    session_data: dict = Depends(get_session_data),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    access_token = session_data.get("access_token")

    if not isinstance(access_token, str) or not access_token:
        raise HTTPException(
            status_code=401,
            detail="Invalid session",
        )

    repository = db.scalar(
        select(Repository).where(
            Repository.github_repo_id == repository_id
        )
    )

    if repository is None:
        raise HTTPException(
            status_code=404,
            detail="Repository not found",
        )

    service = AnalysisService()

    try:
        analysis = await service.analyze_repository(
            db=db,
            access_token=access_token,
            repository_id=repository.id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    return AnalysisResponse(**analysis)