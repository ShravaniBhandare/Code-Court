"""Background runner tests."""

from datetime import datetime, timezone

from app.core.errors import AnalysisCancelled
from app.core.pipeline import AnalysisRequest
from app.db.base import create_engine_from_url, init_db, make_session_factory
from app.db import crud
from app.services.job_runner import JobRunner, _failure


def test_failure_mapping_is_safe():
    code, message = _failure(AnalysisCancelled("cancelled"))
    assert code == "cancelled"
    assert "cancelled" in message.lower()
    assert _failure(RuntimeError("C:\\secret\\traceback")) == (
        "internal_error",
        "Analysis failed unexpectedly",
    )


def test_runner_marks_success_synchronously(tmp_path):
    engine = create_engine_from_url(f"sqlite:///{tmp_path / 'runner.db'}")
    init_db(engine)
    factory = make_session_factory(engine)
    with factory() as session:
        repo = crud.get_or_create_repository(session, "owner", "repo")
        analysis = crud.create_analysis(session, repo.id, "a" * 40, {}, "b" * 64, "1")
        session.commit()

    class Output:
        head_sha = "c" * 40
        anomalies = []
        commit_rows = []
        report_dict = {}
        class Report:
            authors = []
        report = Report()

    runner = JobRunner(factory, pipeline_fn=lambda *args, **kwargs: Output(), synchronous=True)
    runner.submit(analysis.id, AnalysisRequest(tmp_path))
    with factory() as session:
        assert session.get(type(analysis), analysis.id).status == "succeeded"
    runner.shutdown()
