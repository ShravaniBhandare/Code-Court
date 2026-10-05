from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from fastapi import HTTPException

from app.utils import session


def test_session_token_contains_signed_access_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        session,
        "get_settings",
        lambda: SimpleNamespace(
            session_secret="test-session-secret-at-least-32-bytes-long"
        ),
    )

    token = session.create_session_token("github-access-token")
    payload = jwt.decode(
        token,
        "test-session-secret-at-least-32-bytes-long",
        algorithms=[session.JWT_ALGORITHM],
    )

    assert payload["access_token"] == "github-access-token"
    assert payload["exp"] > datetime.now(timezone.utc).timestamp()


def test_session_data_rejects_expired_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        session,
        "get_settings",
        lambda: SimpleNamespace(
            session_secret="test-session-secret-at-least-32-bytes-long"
        ),
    )
    expired_token = jwt.encode(
        {
            "access_token": "github-access-token",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        },
        "test-session-secret-at-least-32-bytes-long",
        algorithm=session.JWT_ALGORITHM,
    )

    with pytest.raises(HTTPException) as error:
        session.get_session_data(session=expired_token)

    assert error.value.status_code == 401
