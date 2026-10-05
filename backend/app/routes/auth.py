from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.database.connection import get_db
from app.services.github_service import GitHubService
from app.services.user_service import UserService
from app.utils.session import create_session_token


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/github/login")
async def github_login() -> RedirectResponse:
    github_service = GitHubService()
    authorization_url = github_service.get_authorization_url()
    return RedirectResponse(url=authorization_url)


@router.get("/github/callback")
async def github_callback(
    code: str,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    settings = get_settings()
    github_service = GitHubService()

    try:
        access_token = await github_service.exchange_code_for_token(code)
        github_user = await github_service.get_authenticated_user(access_token)
        UserService.get_or_create_user(db, github_user)
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail="GitHub authentication failed",
        ) from error

    session_value = create_session_token(access_token)

    response = RedirectResponse(
        url=f"{settings.frontend_url}/repositories",
        status_code=302,
    )
    response.set_cookie(
        key="session",
        value=session_value,
        httponly=True,
        samesite="none",
        secure=True,
    )
    return response