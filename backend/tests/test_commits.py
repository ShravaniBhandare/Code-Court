"""Tests for normalized commit listing."""

from pathlib import Path
import subprocess

import pytest

from app.core.cloner import ensure_clone
from app.core.commits import list_commits
from app.core.github_meta import fetch_repo_meta
from app.core.repo_url import parse_repo_url


def _git(path: Path, *arguments: str) -> None:
    """Run a git command in the fixture repository."""
    subprocess.run(
        ["git", "-C", str(path), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def git_repository(tmp_path: Path) -> Path:
    """Create a small repository with five commits and two authors."""
    repo = tmp_path / "source"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Fixture User")
    _git(repo, "config", "user.email", "fixture@example.com")

    file_path = repo / "notes.txt"
    file_path.write_text("one\ntwo\n", encoding="utf-8")
    _git(repo, "add", "notes.txt")
    _git(repo, "commit", "-q", "-m", "initial", "--author", "Alice <alice@example.com>")

    file_path.write_text("one\ntwo\nthree\nfour\nfive\n", encoding="utf-8")
    _git(repo, "add", "notes.txt")
    _git(repo, "commit", "-q", "-m", "add three lines", "--author", "Alice <alice@example.com>")

    file_path.write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")
    _git(repo, "add", "notes.txt")
    _git(repo, "commit", "-q", "-m", "delete one line", "--author", "Bob <bob@example.com>")

    file_path.write_text("one\ntwo\nthree\nfour\nsix\n", encoding="utf-8")
    _git(repo, "add", "notes.txt")
    _git(repo, "commit", "-q", "-m", "add one line", "--author", "Bob <bob@example.com>")

    file_path.write_text("one\ntwo\nthree\nfour\nseven\n", encoding="utf-8")
    _git(repo, "add", "notes.txt")
    _git(repo, "commit", "-q", "-m", "replace one line", "--author", "Alice <alice@example.com>")
    return repo


def test_list_commits(git_repository: Path) -> None:
    """Commit metadata is normalized and ordered oldest to newest."""
    commits = list_commits(git_repository)

    assert len(commits) == 5
    assert {commit.author_email for commit in commits} == {
        "alice@example.com",
        "bob@example.com",
    }
    assert sum(commit.insertions for commit in commits) == 7
    assert sum(commit.deletions for commit in commits) == 2
    assert commits == sorted(commits, key=lambda commit: commit.authored_at)
    assert commits[1].insertions == 3
    assert commits[2].deletions == 1
    assert all(commit.authored_at.tzinfo is not None for commit in commits)

    newest = list_commits(git_repository, max_commits=2)
    assert [commit.hash for commit in newest] == [commit.hash for commit in commits[-2:]]


@pytest.mark.network
def test_public_repository_pipeline() -> None:
    """The full ingestion pipeline works for a public GitHub repository."""
    owner, repo = parse_repo_url("octocat/Hello-World")
    metadata = fetch_repo_meta(owner, repo)
    clone_path = ensure_clone(owner, repo, metadata["clone_url"])
    assert len(list_commits(clone_path)) > 0
