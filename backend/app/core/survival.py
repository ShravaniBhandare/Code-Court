"""Survival signal aggregation from Git blame."""

from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.config import settings
from app.core.diff_analysis import CommitDiffStats
from app.core import git_blame
from app.core.line_classifier import classify_added_line


@dataclass(frozen=True)
class AuthorSurvival:
    """Survival metrics for one human author."""

    author_key: str
    display_name: str
    display_email: str
    meaningful_added: int
    surviving_lines: int
    survival_rate: float | None
    survival_score: float | None
    ownership_share: float
    low_confidence: bool


@dataclass(frozen=True)
class SurvivalResult:
    """Repository-wide survival metrics."""

    authors: list[AuthorSurvival]
    bot_authors: list[str]
    coverage: float
    partial: bool
    files_blamed: int
    files_skipped: dict[str, int]
    repo_survival_rate: float | None
    ownership_by_dir: dict[str, dict[str, int]]
    accounting: dict[str, int]


def smooth_survival(surviving: int, denominator: int, prior: float, k: int) -> float:
    """Shrink a contributor's survival rate toward the repository prior."""
    if denominator + k == 0:
        return 0.0
    return round((surviving + k * prior) / (denominator + k), 4)


def _most_common(items: list[tuple[str, str]]) -> tuple[str, str]:
    counts = Counter(items)
    return min(counts, key=lambda value: (-counts[value], value[0], value[1]))


def compute_survival(
    repo_path: Path,
    commit_stats: list[CommitDiffStats],
    progress: Callable[[int, int], None] | None = None,
) -> SurvivalResult:
    """Compute the fraction of meaningful additions still present at HEAD."""
    ordered_stats = sorted(commit_stats, key=lambda item: item.hash)
    sha_to_author = {
        item.hash: item.author_key for item in ordered_stats if not item.is_merge
    }
    bot_hashes = {item.hash for item in ordered_stats if not item.is_merge and item.is_bot}
    merge_hashes = {item.hash for item in ordered_stats if item.is_merge}
    grouped: dict[str, list[CommitDiffStats]] = defaultdict(list)
    for item in ordered_stats:
        if not item.is_merge and not item.is_bot:
            grouped[item.author_key].append(item)

    files, _ = git_blame.list_head_source_files(repo_path)
    selected, skipped = git_blame.select_files_for_blame(files)
    coverage = git_blame.compute_coverage(selected, files)
    partial = coverage < settings.MIN_BLAME_COVERAGE
    blame_results: dict[str, list[tuple[str, str]]] = {}
    ignore_revs_file = git_blame.find_ignore_revs_file(repo_path)
    with ThreadPoolExecutor(max_workers=settings.BLAME_WORKERS) as executor:
        futures = {
            executor.submit(git_blame.blame_file, repo_path, item.path, ignore_revs_file): item.path
            for item in selected
        }
        completed = 0
        for future in as_completed(futures):
            path = futures[future]
            completed += 1
            if progress:
                progress(completed, len(selected))
            try:
                blame_results[path] = future.result()
            except git_blame.BlameError:
                skipped["blame failed"] = skipped.get("blame failed", 0) + 1

    surviving: Counter[str] = Counter()
    ownership: dict[str, Counter[str]] = defaultdict(Counter)
    accounting = Counter(
        meaningful_lines_at_head=0,
        attributed_to_humans=0,
        attributed_to_bots=0,
        outside_window=0,
        unattributed=0,
    )
    bot_names: set[str] = set()
    display_by_hash = {item.hash: item.author_name for item in ordered_stats if item.is_bot}
    for source_file in sorted(selected, key=lambda item: item.path):
        blamed = blame_results.get(source_file.path)
        if not blamed:
            if source_file.path in blame_results:
                skipped["binary or empty"] = skipped.get("binary or empty", 0) + 1
            continue
        extension = (
            "." + source_file.path.rsplit(".", 1)[-1].lower()
            if "." in source_file.path.rsplit("/", 1)[-1]
            else ""
        )
        block = False
        top_dir = source_file.path.split("/", 1)[0] if "/" in source_file.path else "."
        for sha, content in blamed:
            category, block = classify_added_line(content, extension, block)
            if category != "meaningful":
                continue
            accounting["meaningful_lines_at_head"] += 1
            if sha in bot_hashes:
                accounting["attributed_to_bots"] += 1
                if sha in display_by_hash:
                    bot_names.add(display_by_hash[sha])
            elif sha in sha_to_author:
                key = sha_to_author[sha]
                accounting["attributed_to_humans"] += 1
                surviving[key] += 1
                ownership[top_dir][key] += 1
            elif sha in merge_hashes or set(sha) == {"0"}:
                accounting["unattributed"] += 1
            else:
                accounting["outside_window"] += 1

    denominators = {key: sum(item.meaningful_added for item in items) for key, items in grouped.items()}
    human_total = sum(surviving.values())
    denominator_total = sum(denominators.values())
    capped_surviving = sum(min(surviving[key], value) for key, value in denominators.items())
    repo_rate = (
        round(capped_surviving / denominator_total, 4) if denominator_total else None
    )
    raw_names = {
        key: _most_common([(item.author_name, item.author_email) for item in items])
        for key, items in grouped.items()
    }
    authors = []
    for key, denominator in denominators.items():
        name, email = raw_names[key]
        rate = round(min(1.0, surviving[key] / denominator), 4) if denominator else None
        score = (
            None
            if partial or repo_rate is None or denominator == 0
            else smooth_survival(
                min(surviving[key], denominator), denominator, repo_rate, settings.SURVIVAL_SHRINK_K
            )
        )
        authors.append(
            AuthorSurvival(
                key, name, email, denominator, surviving[key], rate, score,
                round(surviving[key] / human_total, 4) if human_total else 0.0,
                denominator < settings.MIN_LINES_FOR_SURVIVAL,
            )
        )
    authors.sort(key=lambda item: (-item.surviving_lines, item.display_name))
    return SurvivalResult(
        authors=authors,
        bot_authors=sorted(bot_names),
        coverage=coverage,
        partial=partial,
        files_blamed=len(blame_results),
        files_skipped=dict(sorted(skipped.items())),
        repo_survival_rate=repo_rate,
        ownership_by_dir={
            directory: dict(sorted(counts.items()))
            for directory, counts in sorted(ownership.items())
        },
        accounting=dict(accounting),
    )
