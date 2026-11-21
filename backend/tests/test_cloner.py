"""Tests for repository cloning and cache updates."""

from pathlib import Path
import subprocess

import pytest

from app.config import settings
from app.core.cloner import ensure_clone, get_head_sha


def _git(path: Path, *arguments: str) -> None:
    """Run a git command in the fixture repository."""
    subprocess.run(
        ["git", "-C", str(path), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def local_repository(tmp_path: Path) -> Path:
    """Create a local source repository with one commit."""
    repo = tmp_path / "source"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Fixture User")
    _git(repo, "config", "user.email", "fixture@example.com")
    (repo / "README.md").write_text("fixture\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "initial")
    return repo


def test_ensure_clone_and_update(
    local_repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A source repository can be cloned and refreshed from its local path."""
    monkeypatch.setattr(settings, "CACHE_DIR", str(tmp_path / "cache"))

    clone_path = ensure_clone("owner", "repo", str(local_repository))
    assert clone_path.is_dir()
    assert len(get_head_sha(clone_path)) == 40

    assert ensure_clone("owner", "repo", str(local_repository)) == clone_path
