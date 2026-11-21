"""Tests for commit-level touched-function analysis."""

from pathlib import Path
import subprocess

import pytest
from pydriller import Repository

from app.core.quality_analysis import analyze_commit_quality


def _git(path: Path, *arguments: str) -> None:
    """Run a Git command in a test repository."""
    subprocess.run(["git", "-C", str(path), *arguments], check=True, capture_output=True, text=True)


@pytest.fixture
def quality_repo(tmp_path: Path) -> Path:
    """Build a repository containing an initial and a function commit."""
    repo = tmp_path / "quality"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.com")
    (repo / "app.py").write_text("value = 1\n", encoding="utf-8")
    _git(repo, "add", "app.py")
    _git(repo, "commit", "-q", "-m", "initial")
    (repo / "app.py").write_text(
        "def clean(value):\n"
        "    first = value + 1\n"
        "    second = first + 1\n"
        "    third = second + 1\n"
        "    fourth = third + 1\n"
        "    fifth = fourth + 1\n"
        "    return fifth\n",
        encoding="utf-8",
    )
    _git(repo, "add", "app.py")
    _git(repo, "commit", "-q", "-m", "add function")
    return repo


def test_analyze_commit_quality(quality_repo: Path) -> None:
    """Added lines inside a new function produce one FunctionTouch."""
    commits = list(Repository(str(quality_repo)).traverse_commits())
    result = analyze_commit_quality(commits[-1])
    assert len(result.functions) == 1
    assert result.functions[0].function_name == "clean"
    assert result.functions[0].added_lines_in_function == 7
    assert result.functions[0].weight == 7
