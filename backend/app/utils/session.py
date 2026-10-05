from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Cookie, HTTPException
import jwt
from jwt import InvalidTokenError

from app.config.settings import get_settings


SESSION_DURATION_HOURS = 24
JWT_ALGORITHM = "HS256"


def create_session_token(access_token: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        hours=SESSION_DURATION_HOURS
    )
    return jwt.encode(
        {"access_token": access_token, "exp": expires_at},
        get_settings().session_secret,
        algorithm=JWT_ALGORITHM,
    )


def get_session_data(
    session: str | None = Cookie(default=None),
) -> dict[str, Any]:
    if not session:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
        )

    try:
        session_data = jwt.decode(
            session,
            get_settings().session_secret,
            algorithms=[JWT_ALGORITHM],
        )
    except InvalidTokenError as error:
        raise HTTPException(
            status_code=401,
            detail="Invalid session",
        ) from error

    if not isinstance(session_data, dict):
        raise HTTPException(
            status_code=401,
            detail="Invalid session",
        )

    return session_data