import os
from datetime import datetime, timedelta

from fastapi import Request, HTTPException, status
from jose import jwt, JWTError

JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24


def create_session_token(user_id: int) -> str:
    """Called right after GitHub OAuth succeeds, to issue our own session token."""
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user_id(request: Request) -> int:
    """
    FastAPI dependency: reads the httpOnly 'session' cookie, verifies it,
    and returns the internal user id. Raises 401 if missing/invalid —
    the frontend should catch that and redirect to /login.
    """
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
