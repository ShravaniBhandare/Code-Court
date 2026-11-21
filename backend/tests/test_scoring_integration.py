"""Integration coverage for composing existing signal aggregators."""

from app.core.quality_signal import AuthorQuality
from app.core.scoring import compute_scores
from app.core.size_signal import AuthorSize
from app.core.activity import ActivityData
from app.core.activity_signals import compute_activity_signals


def test_quality_modifier_changes_work_input() -> None:
    size = AuthorSize("a", "A", "a@example.com", 3, 0, 0.0, 10, 10, 10, 0, 0, 0, 0.0)
    quality = AuthorQuality("a", "A", "a@example.com", 5, 5, 1.0, 1, 0, 0.5, 1.2, False)

    report = compute_scores([size], [quality], None)

    assert report.authors[0].adjusted_size == 12.0
    assert report.authors[0].signals["work"].raw_value == 12.0


def test_empty_github_activity_returns_dropped_signals():
    activity = ActivityData([], [], [], [], {}, False, [], 0)
    result = compute_activity_signals(activity, {}, ["author"], "log")
    assert result.review is None
    assert result.issues is None
    assert "review" in result.dropped_reasons
    assert "issues" in result.dropped_reasons
