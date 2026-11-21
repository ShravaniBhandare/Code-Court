"""Commit timing consistency signal."""

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from app.config import settings


@dataclass(frozen=True)
class ConsistencyResult:
    values: dict[str, float] | None
    dropped_reason: str | None
    span_weeks: int
    per_author: dict[str, dict[str, float | int]]


def _utc(value: datetime) -> datetime:
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def compute_consistency(
    commit_stats: list,
    human_author_keys: list[str],
    scaling: str | None = None,
) -> ConsistencyResult:
    """Measure activity spread across the repository's ISO calendar weeks."""
    selected = [
        item for item in commit_stats
        if not item.is_merge and not item.is_bot and not item.is_trivial
        and item.author_key in human_author_keys
    ]
    if not selected:
        return ConsistencyResult(None, "repository history shorter than 3 weeks", 0, {})
    weeks = [_utc(item.authored_at).date().isocalendar() for item in selected]
    first = weeks[0]
    last = weeks[-1]
    first_monday = datetime.fromisocalendar(first.year, first.week, 1).date()
    last_monday = datetime.fromisocalendar(last.year, last.week, 1).date()
    total_weeks = (last_monday - first_monday).days // 7 + 1
    per_author: dict[str, dict[str, float | int]] = {}
    by_author: dict[str, list] = defaultdict(list)
    for item in selected:
        by_author[item.author_key].append(item)
    for key in human_author_keys:
        items = by_author.get(key, [])
        counts = Counter(_utc(item.authored_at).date().isocalendar()[:2] for item in items)
        lines = sum(item.meaningful_added for item in items)
        max_share = max(counts.values(), default=0) / lines if lines else 0.0
        per_author[key] = {
            "active_weeks": len(counts),
            "total_weeks": total_weeks,
            "max_week_share": round(max_share, 4),
        }
    if total_weeks < settings.MIN_SPAN_WEEKS:
        return ConsistencyResult(None, "repository history shorter than 3 weeks", total_weeks, per_author)
    values = {
        key: round(
            max(
                0.0,
                min(
                    1.0,
                    0.6 * item["active_weeks"] / total_weeks
                    + 0.4 * (1 - item["max_week_share"]),
                ),
            ),
            4,
        )
        for key, item in per_author.items()
    }
    return ConsistencyResult(values, None, total_weeks, per_author)
