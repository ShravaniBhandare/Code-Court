"""Shared helpers for temporary Git repositories."""

from pathlib import Path
import subprocess


def git(path: Path, *arguments: str) -> None:
    """Run a Git command in a temporary repository."""
    subprocess.run(
        ["git", "-C", str(path), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )


def commit_file(
    repo: Path,
    relative_path: str,
    content: str,
    message: str,
    name: str = "Test User",
    email: str = "test@example.com",
    author_date: str | None = None,
    committer_date: str | None = None,
) -> None:
    """Write, stage, and commit one file with the selected author."""
    target = repo / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    git(repo, "add", relative_path)
    environment = {
        "GIT_AUTHOR_NAME": name,
        "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": name,
        "GIT_COMMITTER_EMAIL": email,
    }
    if author_date:
        environment["GIT_AUTHOR_DATE"] = author_date
    if committer_date:
        environment["GIT_COMMITTER_DATE"] = committer_date
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", message],
        check=True,
        capture_output=True,
        text=True,
        env={**__import__("os").environ, **environment},
    )
