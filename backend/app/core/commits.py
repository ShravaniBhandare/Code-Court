"""Commit listing through PyDriller."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pydriller import Repository

from app.config import settings


@dataclass(frozen=True)
class CommitInfo:
    """Cheap, normalized commit metadata."""

    hash: str
    author_name: str
    author_email: str
    authored_at: datetime
    message_first_line: str
    is_merge: bool
    files_changed: int
    insertions: int
    deletions: int
    parents: int


def _aware(value: datetime) -> datetime:
    """Ensure a commit timestamp is timezone-aware."""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def list_commits(
    repo_path: Path,
    max_commits: int | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[CommitInfo]:
    """List commits oldest to newest without loading modified files."""
    limit = settings.DEFAULT_MAX_COMMITS if max_commits is None else max_commits
    if limit < 0:
        raise ValueError("max_commits must be non-negative.")

    commits: list[CommitInfo] = []
    for commit in Repository(str(repo_path), since=since, to=until).traverse_commits():
        commits.append(
            CommitInfo(
                hash=commit.hash,
                author_name=commit.author.name,
                author_email=commit.author.email,
                authored_at=_aware(commit.author_date),
                message_first_line=commit.msg.splitlines()[0].strip()
                if commit.msg.splitlines()
                else "",
                is_merge=commit.merge,
                files_changed=commit.files,
                insertions=commit.insertions,
                deletions=commit.deletions,
                parents=len(commit.parents),
            )
        )
    return commits[-limit:] if limit else []
