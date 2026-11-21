"""Tests for author quality aggregation."""

from datetime import datetime, timezone

from app.core.quality_analysis import CommitQualityStats, FunctionTouch
from app.core.quality_signal import adjusted_size, compute_quality_signal


def _stats(key: str, name: str, quality: float, count: int = 5, bot: bool = False):
    """Build repeated function stats for aggregation tests."""
    function = FunctionTouch("src.py", "f", 2, 10, 1, 3, 10, quality)
    return CommitQualityStats(
        "hash", key, name, f"{key}@example.com", bot, tuple(function for _ in range(count)), {}
    )


def test_quality_modifier_and_determinism() -> None:
    """Quality maps to bounded modifiers and shuffled input is stable."""
    stats = [_stats("a", "Alice", 1.0), _stats("b", "Bob", 0.0), _stats("bot", "build[bot]", 1.0, bot=True)]
    humans, bots = compute_quality_signal(list(reversed(stats)))
    assert humans[0].quality_modifier == 1.2
    assert humans[1].quality_modifier == 0.7
    assert bots[0].display_name == "build[bot]"
    assert compute_quality_signal(stats) == (humans, bots)
    assert adjusted_size(400, 1.2) == 480.0


def test_low_confidence_and_empty() -> None:
    """Authors with too few functions receive a neutral modifier."""
    humans, bots = compute_quality_signal([_stats("a", "Alice", 0.0, count=1)])
    assert humans[0].quality_modifier == 1.0
    assert humans[0].low_confidence
    assert bots == []
    assert compute_quality_signal([]) == ([], [])
