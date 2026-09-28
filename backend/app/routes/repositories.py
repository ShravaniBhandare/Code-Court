from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.repository import RepositoryListResponse
from app.services.repository_service import RepositoryService
from app.utils.session import get_session_data


router = APIRouter(prefix="/api/repositories", tags=["repositories"])


@router.get("", response_model=RepositoryListResponse)
async def list_repositories(
    session_data: dict = Depends(get_session_data),
    db: Session = Depends(get_db),
) -> RepositoryListResponse:
    access_token = session_data.get("access_token")

    if not isinstance(access_token, str) or not access_token:
        raise HTTPException(
            status_code=401,
            detail="Invalid session",
        )

    service = RepositoryService()
    repositories = await service.list_repositories(
        db=db,
        access_token=access_token,
    )

    return RepositoryListResponse(repositories=repositories)