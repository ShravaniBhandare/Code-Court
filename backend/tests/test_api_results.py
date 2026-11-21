"""Result endpoint contract tests."""

from fastapi.testclient import TestClient

from app.main import app


def test_unfinished_results_are_not_ready():
    with TestClient(app) as client:
        response = client.get("/scores/does-not-exist")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "analysis_not_found"


def test_pdf_endpoint_requires_completed_analysis():
    with TestClient(app) as client:
        response = client.get("/reports/does-not-exist/pdf")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "analysis_not_found"
