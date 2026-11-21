"""Tests for the survival signal."""

from pathlib import Path

from pydriller import Repository

from app.core.diff_analysis import analyze_commit
from app.core.survival import compute_survival, smooth_survival
from tests.conftest import commit_file, git


def test_smoothing_math() -> None:
    assert smooth_survival(80, 100, 0.6, 20) == 0.7667


def test_basic_survival_and_accounting(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.com")
    initial = "\n".join(f"value_{i} = {i}" for i in range(10)) + "\n"
    commit_file(repo, "app.py", initial, "Alice", "Alice", "alice@example.com")
    changed = "\n".join(
        (f"value_{i} = {i}" if i < 5 else f"new_value_{i} = {i}")
        for i in range(10)
    ) + "\n"
    commit_file(repo, "app.py", changed, "Bob", "Bob", "bob@example.com")
    commits = [
        analyze_commit(commit)
        for commit in Repository(str(repo), only_no_merge=False).traverse_commits()
    ]

    result = compute_survival(repo, commits)
    authors = {author.display_name: author for author in result.authors}

    assert authors["Alice"].meaningful_added == 10
    assert authors["Alice"].surviving_lines == 5
    assert authors["Bob"].meaningful_added == 5
    assert authors["Bob"].surviving_lines == 5
    assert result.accounting["meaningful_lines_at_head"] == 10
    assert result.accounting["meaningful_lines_at_head"] == sum(
        result.accounting[key]
        for key in (
            "attributed_to_humans",
            "attributed_to_bots",
            "outside_window",
            "unattributed",
        )
    )
