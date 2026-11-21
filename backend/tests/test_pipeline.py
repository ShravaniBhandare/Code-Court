"""Shared pipeline tests."""

import json
from pathlib import Path

import pytest

from app.core.errors import AnalysisTimeout
from app.core.pipeline import AnalysisRequest, normalized_params, params_hash, run_pipeline


def test_params_are_canonical():
    first = AnalysisRequest("owner/repo", weights={"work": 1}, scaling="linear")
    second = AnalysisRequest("owner/repo", weights={"work": 1}, scaling="linear")
    assert params_hash(first) == params_hash(second)
    assert normalized_params(first)["weights"]["work"] == 1.0


def test_pipeline_stop_callback_propagates(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(AnalysisTimeout):
        run_pipeline(
            AnalysisRequest(repo),
            should_stop=lambda: (_ for _ in ()).throw(AnalysisTimeout("stop")),
        )
