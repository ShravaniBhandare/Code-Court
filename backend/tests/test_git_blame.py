"""Tests for the Git blame adapter."""

from pathlib import Path

import pytest

from app.config import settings
from app.core.git_blame import (
    BlameError,
    SourceFile,
    blame_file,
    compute_coverage,
    find_ignore_revs_file,
    list_head_source_files,
    select_files_for_blame,
)
from tests.conftest import commit_file, git


def test_list_head_source_files_filters_tracked_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.com")
    commit_file(repo, "app.py", "value = 1\n", "source")
    (repo / "README.md").write_text("readme\n", encoding="utf-8")
    (repo / "package-lock.json").write_text("{}\n", encoding="utf-8")
    (repo / "node_modules").mkdir()
    (repo / "node_modules" / "ignored.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "image.png").write_bytes(b"\x89PNG")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "other files")

    files, info = list_head_source_files(repo)

    assert files == [SourceFile("app.py", 10)]
    assert info == {"total_source_files": 1, "total_source_bytes": 10}


def test_select_files_and_compute_coverage(monkeypatch: pytest.MonkeyPatch) -> None:
    files = [SourceFile("small.py", 10), SourceFile("large.py", 20)]
    monkeypatch.setattr(settings, "MAX_BLAME_FILE_BYTES", 15)
    monkeypatch.setattr(settings, "MAX_BLAME_FILES", 1)

    selected, skipped = select_files_for_blame(files)

    assert selected == [SourceFile("small.py", 10)]
    assert skipped == {"too large": 1}
    assert compute_coverage(selected, files) == pytest.approx(1 / 3)


def test_blame_file_and_missing_path(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.com")
    commit_file(repo, "app.py", "one = 1\ntwo = 2\n", "source")

    result = blame_file(repo, "app.py", None)
    assert len(result) == 2
    assert [line for _, line in result] == ["one = 1", "two = 2"]
    with pytest.raises(BlameError):
        blame_file(repo, "missing.py", None)


def test_find_ignore_revs_file(tmp_path: Path) -> None:
    assert find_ignore_revs_file(tmp_path) is None
    path = tmp_path / ".git-blame-ignore-revs"
    path.write_text("0" * 40, encoding="utf-8")
    assert find_ignore_revs_file(tmp_path) == path
