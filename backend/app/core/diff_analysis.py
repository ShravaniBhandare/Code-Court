"""Diff analysis for triviality and meaningful-line signals."""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from pydriller import Repository

from app.config import settings
from app.core.author_key import author_key, is_probably_bot
from app.core.file_filters import classify_path, LANGUAGE_BY_EXT
from app.core.line_classifier import classify_added_line
from app.core.quality_analysis import CommitQualityStats, analyze_commit_quality


@dataclass(frozen=True)
class FileDiffStats:
    """Normalized statistics for one modified file."""

    path: str
    category: str
    change_type: str
    raw_added: int
    raw_deleted: int
    blank: int
    comment: int
    import_: int
    punctuation: int
    formatting_churn: int
    meaningful_added: int
    skipped_reason: str | None


@dataclass(frozen=True)
class CommitDiffStats:
    """Normalized statistics for one commit."""

    hash: str
    author_key: str
    author_name: str
    author_email: str
    authored_at: datetime
    is_merge: bool
    is_bot: bool
    files_total: int
    files_source: int
    raw_added: int
    meaningful_added: int
    meaningful_credited: int
    docs_lines_added: int
    config_lines_added: int
    ignored_files: int
    is_bulk: bool
    is_trivial: bool
    skipped_files: list[str]


def _change_type(file: Any) -> str:
    """Return a stable change type string across PyDriller versions."""
    value = getattr(file, "change_type", "")
    return getattr(value, "name", str(value)).upper()


def _normalized(value: str) -> str:
    """Remove whitespace for formatting-churn matching."""
    return "".join(value.split())


def _file_stats(file: Any) -> FileDiffStats:
    """Analyze one PyDriller modified-file object."""
    path = file.new_path or file.old_path or ""
    category = classify_path(path)
    change_type = _change_type(file)
    parsed = file.diff_parsed
    if parsed is None or "\x00" in (file.diff or ""):
        return FileDiffStats(path, category, change_type, 0, 0, 0, 0, 0, 0, 0, 0, "binary")
    added = list(parsed.get("added", []))
    deleted = list(parsed.get("deleted", []))
    if change_type == "RENAME" and not added and not deleted:
        return FileDiffStats(path, category, change_type, 0, 0, 0, 0, 0, 0, 0, 0, "pure rename")
    if not added and not deleted:
        return FileDiffStats(path, category, change_type, 0, 0, 0, 0, 0, 0, 0, 0, "binary")
    if len(added) > settings.MAX_FILE_DIFF_LINES:
        return FileDiffStats(
            path, category, change_type, len(added), len(deleted), 0, 0, 0, 0, 0, 0,
            "too large (likely generated or pasted)",
        )

    deleted_lines = Counter(_normalized(text) for _, text in deleted if _normalized(text))
    counts = Counter()
    meaningful = 0
    churn = 0
    block = False
    ext = "." + path.rsplit(".", 1)[-1].lower() if "." in path.rsplit("/", 1)[-1] else ""
    for _, text in added:
        normalized = _normalized(text)
        if normalized and deleted_lines[normalized]:
            deleted_lines[normalized] -= 1
            churn += 1
            continue
        line_category, block = classify_added_line(text, ext, block)
        counts[line_category] += 1
        if line_category == "meaningful" and category == "source":
            meaningful += 1
    return FileDiffStats(
        path=path,
        category=category,
        change_type=change_type,
        raw_added=len(added),
        raw_deleted=len(deleted),
        blank=counts["blank"],
        comment=counts["comment"],
        import_=counts["import"],
        punctuation=counts["punctuation"],
        formatting_churn=churn,
        meaningful_added=meaningful,
        skipped_reason=None,
    )


def analyze_commit(commit: Any) -> CommitDiffStats:
    """Analyze one commit and never load diffs for merge commits."""
    author = commit.author
    key = author_key(author.name, author.email)
    bot = is_probably_bot(author.name, author.email)
    if commit.merge:
        return CommitDiffStats(
            commit.hash, key, author.name, author.email, commit.author_date, True, bot,
            0, 0, 0, 0, 0, 0, 0, 0, False, True, [],
        )

    files = list(commit.modified_files)
    stats: list[FileDiffStats] = []
    skipped: list[str] = []
    for file in files:
        try:
            result = _file_stats(file)
        except Exception as error:
            path = file.new_path or file.old_path or ""
            result = FileDiffStats(
                path, classify_path(path), _change_type(file), 0, 0, 0, 0, 0, 0, 0, 0,
                f"error: {type(error).__name__}",
            )
        stats.append(result)
        if result.skipped_reason:
            skipped.append(result.skipped_reason)

    meaningful = sum(item.meaningful_added for item in stats)
    return CommitDiffStats(
        hash=commit.hash,
        author_key=key,
        author_name=author.name,
        author_email=author.email,
        authored_at=commit.author_date,
        is_merge=False,
        is_bot=bot,
        files_total=len(files),
        files_source=sum(item.category == "source" for item in stats),
        raw_added=sum(item.raw_added for item in stats),
        meaningful_added=meaningful,
        meaningful_credited=min(meaningful, settings.COMMIT_MEANINGFUL_CAP),
        docs_lines_added=sum(item.raw_added for item in stats if item.category == "docs"),
        config_lines_added=sum(item.raw_added for item in stats if item.category == "config"),
        ignored_files=sum(item.category == "ignored" for item in stats),
        is_bulk=len(files) > settings.MAX_FILES_PER_COMMIT,
        is_trivial=meaningful < settings.TRIVIAL_COMMIT_THRESHOLD,
        skipped_files=skipped,
    )


def analyze_repo(
    repo_path: Any,
    max_commits: int | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> list[CommitDiffStats]:
    """Analyze the newest selected commits in repository order."""
    results, _ = _analyze_repo_selected(
        repo_path, max_commits, since, until, progress, include_quality=False
    )
    return results


def _analyze_repo_selected(
    repo_path: Any,
    max_commits: int | None,
    since: datetime | None,
    until: datetime | None,
    progress: Callable[[int, int], None] | None,
    include_quality: bool,
) -> tuple[list[CommitDiffStats], list[CommitQualityStats]]:
    """Traverse the selected newest commits once for one or both analyses."""
    limit = settings.DEFAULT_MAX_COMMITS if max_commits is None else max_commits
    if limit < 0:
        raise ValueError("max_commits must be non-negative.")
    hashes = [
        commit.hash
        for commit in Repository(
            str(repo_path), since=since, to=until, only_no_merge=False
        ).traverse_commits()
    ]
    selected = hashes[-limit:] if limit else []
    diff_results: list[CommitDiffStats] = []
    quality_results: list[CommitQualityStats] = []
    for index, commit in enumerate(
        Repository(
            str(repo_path), since=since, to=until, only_no_merge=False,
            only_commits=selected,
        ).traverse_commits(),
        start=1,
    ):
        diff_results.append(analyze_commit(commit))
        if include_quality:
            quality_results.append(analyze_commit_quality(commit))
        if progress and index % 25 == 0:
            progress(index, len(selected))
    return diff_results, quality_results


def analyze_repo_full(
    repo_path: Any,
    max_commits: int | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> tuple[list[CommitDiffStats], list[CommitQualityStats]]:
    """Analyze Stage 3 and Stage 4 signals in one commit traversal."""
    return _analyze_repo_selected(
        repo_path, max_commits, since, until, progress, include_quality=True
    )
