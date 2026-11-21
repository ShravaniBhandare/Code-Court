"""Tests for Lizard metrics and scoring curves."""

from app.core.function_metrics import (
    FunctionInfo,
    analyze_source,
    complexity_score,
    function_quality,
    params_score,
    size_score,
)


def test_analyze_python_function() -> None:
    """Python functions are mapped to the public metric dataclass."""
    functions = analyze_source("example.py", "def clean(value):\n    return value\n")
    assert len(functions) == 1
    assert functions[0].name == "clean"
    assert functions[0].parameter_count == 1
    assert function_quality(functions[0]) == 0.58


def test_unsupported_and_invalid_source_return_empty() -> None:
    """Unsupported or invalid sources never raise."""
    assert analyze_source("notes.xyz", "not source") == []
    assert analyze_source("broken.py", "def broken(:\n") == []


def test_scoring_curves() -> None:
    """Curve boundary values stay within the expected range."""
    assert [complexity_score(value) for value in (1, 2, 3, 15, 27, 39, 60)] == [
        0.3, 0.65, 1.0, 1.0, 0.6, 0.2, 0.2
    ]
    assert size_score(10) == 1.0
    assert size_score(40) == 1.0
    assert size_score(150) == 0.3
    assert params_score(4) == 1.0
    assert params_score(8) == 0.5
    assert params_score(12) == 0.4
    assert all(0.0 <= value <= 1.0 for value in (size_score(95), params_score(5)))


def test_source_size_limit(monkeypatch) -> None:
    """Oversized source is skipped."""
    from app.config import settings

    monkeypatch.setattr(settings, "LIZARD_MAX_FILE_BYTES", 1)
    assert analyze_source("x.py", "def f():\n    pass\n") == []
