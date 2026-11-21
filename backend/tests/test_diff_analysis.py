"""Tests for per-commit diff analysis."""

from pathlib import Path
import subprocess

import pytest
from pydriller import Repository

from app.core.diff_analysis import analyze_commit


def _git(path: Path, *arguments: str) -> None:
    """Run a Git command in a test repository."""
    subprocess.run(
        ["git", "-C", str(path), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def analysis_repo(tmp_path: Path) -> Path:
    """Create a repository with code, comments, and documentation commits."""
    repo = tmp_path / "analysis"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.com")
    (repo / "app.py").write_text("one = 1\n", encoding="utf-8")
    _git(repo, "add", "app.py")
    _git(repo, "commit", "-q", "-m", "initial")
    (repo / "app.py").write_text(
        "one = 1\ntwo = 2\nthree = 3\nfour = 4\nfive = 5\n",
        encoding="utf-8",
    )
    _git(repo, "add", "app.py")
    _git(repo, "commit", "-q", "-m", "add code")
    (repo / "README.md").write_text("# Notes\n\nA note.\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "add docs")
    return repo


def test_analyze_commit_counts_source_and_docs(analysis_repo: Path) -> None:
    """Source lines are credited while documentation is tracked separately."""
    commits = list(
        Repository(str(analysis_repo), only_no_merge=False).traverse_commits()
    )
    source = analyze_commit(commits[1])
    docs = analyze_commit(commits[2])

    assert source.meaningful_added == 4
    assert source.meaningful_credited == 4
    assert not source.is_trivial
    assert docs.meaningful_added == 0
    assert docs.docs_lines_added == 3
    assert docs.is_trivial
