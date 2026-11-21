"""Analysis API contract tests."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_and_validation_error_format():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok", "service": "codecourt"}
        response = client.post("/analyze", json={"repo_url": "not-a-url", "unexpected": True})
        assert response.status_code == 422
        assert response.json()["error"]["code"] in {"validation_error", "invalid_url"}


def test_unknown_analysis_is_not_found():
    with TestClient(app) as client:
        response = client.get("/analyses/does-not-exist")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "analysis_not_found"
