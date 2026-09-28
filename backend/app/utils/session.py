from typing import Any

from fastapi import Cookie, HTTPException
from itsdangerous import BadSignature, URLSafeSerializer

from app.config.settings import get_settings


def get_session_data(
    session: str | None = Cookie(default=None),
) -> dict[str, Any]:
    if not session:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
        )

    serializer = URLSafeSerializer(
        get_settings().session_secret,
        salt="codecourt-session",
    )

    try:
        session_data = serializer.loads(session)
    except BadSignature as error:
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