"""Tests for author size aggregation."""

from datetime import datetime, timezone

from app.core.diff_analysis import CommitDiffStats
from app.core.size_signal import compute_size_signal


def _stat(
    key: str,
    name: str,
    email: str,
    credited: int,
    trivial: bool = False,
    bot: bool = False,
) -> CommitDiffStats:
    """Build a compact commit statistic for aggregation tests."""
    return CommitDiffStats(
        key, key, name, email, datetime.now(timezone.utc), False, bot, 1, 1,
        credited, credited, credited, 0, 0, 0, False, trivial, [],
    )


def test_size_signal_is_deterministic_and_excludes_bots() -> None:
    """Humans are ranked and bots are returned separately."""
    stats = [
        _stat("a@example.com", "Alice", "a@example.com", 10),
        _stat("a@example.com", "ALICE", "a@example.com", 5, True),
        _stat("b@example.com", "Bob", "b@example.com", 5),
        _stat("bot", "renovate[bot]", "bot@example.com", 100, bot=True),
    ]
    humans, bots = compute_size_signal(list(reversed(stats)))

    assert [item.display_name for item in humans] == ["ALICE", "Bob"]
    assert humans[0].size_score == 1.0
    assert 0 < humans[1].size_score < 1
    assert humans[0].trivial_ratio == 0.5
    assert [item.display_name for item in bots] == ["renovate[bot]"]
    assert compute_size_signal(stats) == (humans, bots)


def test_zero_and_empty_size_signal() -> None:
    """Empty and zero-credit inputs do not divide by zero."""
    assert compute_size_signal([]) == ([], [])
    humans, bots = compute_size_signal([_stat("a", "A", "", 0, True)])
    assert humans[0].size_score == 0.0
    assert bots == []
