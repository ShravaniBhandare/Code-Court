"""Transparent, rule-based anomaly flags."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.core.author_key import is_probably_bot
from app.core.size_signal import AuthorSize
from app.core.survival import SurvivalResult


@dataclass(frozen=True)
class AnomalyConfig:
    flood_window_minutes: int = 60
    flood_min_commits: int = 10
    flood_trivial_share_warning: float = 0.5
    last_minute_days: int = 3
    last_minute_min_span_days: int = 14
    last_minute_share: float = 0.6
    last_minute_share_warning: float = 0.8
    last_minute_min_lines: int = 100
    last_minute_vs_team_margin: float = 0.2
    trivial_ratio_warning: float = 0.6
    trivial_min_commits: int = 10
    dump_share: float = 0.7
    dump_min_lines: int = 500
    low_survival_rate: float = 0.3
    low_survival_min_lines: int = 100
    penalty_flood: float = 0.95
    penalty_last_minute: float = 0.90
    penalty_trivial: float = 0.90
    enable_penalties: bool = True


@dataclass(frozen=True)
class Anomaly:
    kind: str
    author_key: str
    display_name: str
    severity: str
    message: str
    evidence: dict
    penalty_multiplier: float


def _utc(value: datetime) -> datetime:
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def detect_anomalies(
    commit_stats: list,
    sizes: list[AuthorSize],
    survival: SurvivalResult | None,
    config: AnomalyConfig | None = None,
    deadline: datetime | None = None,
) -> list[Anomaly]:
    """Find neutral, numeric patterns that merit human review."""
    config = config or AnomalyConfig()
    names = {item.author_key: item.display_name for item in sizes}
    human = [
        item for item in commit_stats
        if not item.is_merge and not item.is_bot and item.author_key in names
    ]
    grouped: dict[str, list] = defaultdict(list)
    for item in human:
        grouped[item.author_key].append(item)
    anomalies: list[Anomaly] = []
    for key, items in grouped.items():
        ordered = sorted(items, key=lambda item: (_utc(item.authored_at), item.hash))
        left = 0
        for right, current in enumerate(ordered):
            while _utc(current.authored_at) - _utc(ordered[left].authored_at) > timedelta(minutes=config.flood_window_minutes):
                left += 1
            window = ordered[left:right + 1]
            if len(window) >= config.flood_min_commits:
                trivial = sum(item.is_trivial for item in window) / len(window)
                severity = "warning" if trivial >= config.flood_trivial_share_warning else "info"
                anomalies.append(Anomaly(
                    "commit_flood", key, names[key], severity,
                    f"{len(window)} commits within {config.flood_window_minutes} minutes ({sum(item.is_trivial for item in window)} trivial) on {_utc(window[0].authored_at).date().isoformat()}",
                    {"window_start": _utc(window[0].authored_at).isoformat(), "window_end": _utc(current.authored_at).isoformat(), "commit_count": len(window), "trivial_share": round(trivial, 4), "commits": [item.hash for item in window[:5]]},
                    config.penalty_flood if severity == "warning" else 1.0,
                ))
                break
    if human:
        end = _utc(deadline) if deadline else max(_utc(item.authored_at) for item in human)
        start = min(_utc(item.authored_at) for item in human)
        if (end - start).days >= config.last_minute_min_span_days:
            window_start = end - timedelta(days=config.last_minute_days)
            total_lines = sum(item.meaningful_added for item in human)
            team_window = sum(item.meaningful_added for item in human if window_start <= _utc(item.authored_at) <= end)
            team_share = team_window / total_lines if total_lines else 0.0
            for key, items in grouped.items():
                lines = sum(item.meaningful_added for item in items)
                window_lines = sum(item.meaningful_added for item in items if window_start <= _utc(item.authored_at) <= end)
                share = window_lines / lines if lines else 0.0
                if share >= config.last_minute_share and window_lines >= config.last_minute_min_lines and share - team_share >= config.last_minute_vs_team_margin:
                    severity = "warning" if share >= config.last_minute_share_warning else "info"
                    anomalies.append(Anomaly("last_minute_burst", key, names[key], severity, f"{share:.0%} of {lines} meaningful lines were added in the final {config.last_minute_days} days versus {team_share:.0%} for the team", {"share": round(share, 4), "team_share": round(team_share, 4), "lines": window_lines, "window_start": window_start.isoformat(), "window_end": end.isoformat()}, config.penalty_last_minute if severity == "warning" else 1.0))
    for size in sizes:
        items = grouped.get(size.author_key, [])
        if size.commits >= config.trivial_min_commits and size.trivial_ratio >= config.trivial_ratio_warning:
            anomalies.append(Anomaly("trivial_inflation", size.author_key, size.display_name, "warning", f"{size.trivial_ratio:.0%} of {size.commits} commits were trivial", {"commits": size.commits, "trivial_ratio": size.trivial_ratio}, config.penalty_trivial))
        total = sum(item.meaningful_added for item in items)
        if total:
            largest = max(items, key=lambda item: (item.meaningful_added, item.hash))
            share = largest.meaningful_added / total
            if share >= config.dump_share and largest.meaningful_added >= config.dump_min_lines:
                anomalies.append(Anomaly("single_commit_dump", size.author_key, size.display_name, "info", f"one commit added {largest.meaningful_added} of {total} meaningful lines ({share:.0%})", {"commit": largest.hash, "lines": largest.meaningful_added, "share": round(share, 4)}, 1.0))
    if survival and not survival.partial:
        for author in survival.authors:
            if author.survival_rate is not None and author.survival_rate < config.low_survival_rate and author.meaningful_added >= config.low_survival_min_lines:
                anomalies.append(Anomaly("low_survival", author.author_key, author.display_name, "info", f"{author.survival_rate:.0%} of {author.meaningful_added} meaningful lines survived; most were later rewritten or removed", {"survival_rate": author.survival_rate, "meaningful_added": author.meaningful_added}, 1.0))
    return sorted(anomalies, key=lambda item: (0 if item.severity == "warning" else 1, item.display_name, item.kind))


def build_penalties(anomalies: list[Anomaly], config: AnomalyConfig | None = None) -> dict[str, tuple[float, str]]:
    """Combine warning penalties with a 0.5 minimum."""
    config = config or AnomalyConfig()
    if not config.enable_penalties:
        return {}
    grouped: dict[str, list[Anomaly]] = defaultdict(list)
    for anomaly in anomalies:
        if anomaly.severity == "warning":
            grouped[anomaly.author_key].append(anomaly)
    return {
        key: (max(0.5, min(1.0, _product(item.penalty_multiplier for item in items))), "; ".join(item.kind for item in items))
        for key, items in grouped.items()
    }


def _product(values: list[float]) -> float:
    result = 1.0
    for value in values:
        result *= value
    return result


# Copied-code and re-attribution detection remain future work.
