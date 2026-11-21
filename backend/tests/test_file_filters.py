"""Tests for changed-file classification."""

import pytest

from app.core.file_filters import classify_path


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("node_modules/x/index.js", "ignored"),
        ("package-lock.json", "ignored"),
        ("src/app.min.js", "ignored"),
        ("README.md", "docs"),
        ("docs/guide.html", "docs"),
        ("config.yaml", "config"),
        ("src/Main.java", "source"),
        (r"src\win\path.py", "source"),
        ("Dockerfile", "config"),
        ("unknown.extension", "ignored"),
    ],
)
def test_classify_path(path: str, expected: str) -> None:
    """Known path patterns map to their expected category."""
    assert classify_path(path) == expected
