"""Per-author quality aggregation and bounded modifier."""

from collections import Counter, defaultdict
from dataclasses import dataclass

from app.config import settings
from app.core.author_key import is_probably_bot
from app.core.quality_analysis import CommitQualityStats, FunctionTouch


@dataclass(frozen=True)
class AuthorQuality:
    """Aggregated quality metrics for one author."""

    author_key: str
    display_name: str
    display_email: str
    functions_analyzed: int
    total_weight: int
    avg_complexity: float
    max_complexity: int
    long_functions: int
    quality_score: float
    quality_modifier: float
    low_confidence: bool


def _most_frequent(values: list[str]) -> str:
    """Choose the most frequent value with alphabetical tie-breaking."""
    counts = Counter(values)
    return sorted(counts, key=lambda value: (-counts[value], value))[0]


def _build(items: list[CommitQualityStats]) -> AuthorQuality:
    """Build one deterministic author quality record."""
    functions = [function for item in items for function in item.functions]
    total_weight = sum(function.weight for function in functions)
    quality = (
        sum(function.quality * function.weight for function in functions) / total_weight
        if total_weight
        else 0.0
    )
    low_confidence = len(functions) < settings.MIN_FUNCTIONS_FOR_QUALITY
    modifier = (
        1.0
        if low_confidence
        else settings.QUALITY_MOD_MIN
        + (settings.QUALITY_MOD_MAX - settings.QUALITY_MOD_MIN) * quality
    )
    return AuthorQuality(
        author_key=items[0].author_key,
        display_name=_most_frequent([item.author_name for item in items]),
        display_email=_most_frequent([item.author_email for item in items]),
        functions_analyzed=len(functions),
        total_weight=total_weight,
        avg_complexity=round(
            sum(function.cyclomatic_complexity * function.weight for function in functions)
            / total_weight,
            2,
        ) if total_weight else 0.0,
        max_complexity=max((function.cyclomatic_complexity for function in functions), default=0),
        long_functions=sum(function.nloc > 100 for function in functions),
        quality_score=round(quality, 4),
        quality_modifier=round(modifier, 4),
        low_confidence=low_confidence,
    )


def compute_quality_signal(
    stats: list[CommitQualityStats],
) -> tuple[list[AuthorQuality], list[AuthorQuality]]:
    """Aggregate quality stats into humans and bots."""
    grouped: dict[str, list[CommitQualityStats]] = defaultdict(list)
    for item in stats:
        if not item.author_key:
            continue
        grouped[item.author_key].append(item)
    humans: list[AuthorQuality] = []
    bots: list[AuthorQuality] = []
    for items in grouped.values():
        result = _build(items)
        (bots if is_probably_bot(items[0].author_name, items[0].author_email) else humans).append(result)
    humans.sort(key=lambda item: (-item.quality_score, item.display_name))
    bots.sort(key=lambda item: (-item.quality_score, item.display_name))
    return humans, bots


def adjusted_size(credited_lines: int, modifier: float) -> float:
    """Apply a bounded quality modifier to credited lines."""
    return round(credited_lines * modifier, 2)
