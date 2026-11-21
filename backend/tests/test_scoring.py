"""Tests for contribution scoring."""

from app.core.quality_signal import AuthorQuality
from app.core.scoring import compute_scores
from app.core.size_signal import AuthorSize
from app.core.survival import AuthorSurvival, SurvivalResult


def _size(key: str, name: str, credited: int) -> AuthorSize:
    return AuthorSize(key, name, f"{key}@example.com", 3, 0, 0.0, credited, credited, credited, 0, 0, 0, 0.0)


def _quality(key: str, name: str, modifier: float = 1.0) -> AuthorQuality:
    return AuthorQuality(key, name, f"{key}@example.com", 5, 5, 1.0, 1, 0, 0.5, modifier, False)


def _survival() -> SurvivalResult:
    return SurvivalResult(
        [
            AuthorSurvival("alice", "Alice", "alice@example.com", 10, 8, 0.8, 0.75, 0.6, False),
            AuthorSurvival("bob", "Bob", "bob@example.com", 5, 2, 0.4, 0.45, 0.4, False),
        ],
        [], 1.0, False, 1, {}, 0.6, {}, {
            "meaningful_lines_at_head": 10, "attributed_to_humans": 10,
            "attributed_to_bots": 0, "outside_window": 0, "unattributed": 0,
        },
    )


def test_scores_are_ranked_and_breakdowns_are_complete() -> None:
    report = compute_scores(
        [_size("alice", "Alice", 100), _size("bob", "Bob", 20)],
        [_quality("alice", "Alice", 1.2), _quality("bob", "Bob", 0.8)],
        _survival(),
    )

    assert [item.display_name for item in report.authors] == ["Alice", "Bob"]
    assert set(report.authors[0].signals) == {"work", "survival", "ownership", "review", "issues", "consistency"}
    assert sum(report.effective_weights.values()) == 1.0
    assert sum(
        author.signals[name].points
        for author in report.authors
        for name in report.available_signals
    ) >= 0


def test_unavailable_survival_is_renormalized_and_penalty_is_clamped() -> None:
    report = compute_scores(
        [_size("alice", "Alice", 10)],
        [],
        None,
        penalties={"alice": (0.1, "anomaly")},
    )
    author = report.authors[0]

    assert report.available_signals == ["work"]
    assert author.penalty_multiplier == 0.5
    assert author.signals["survival"].note == "survival not computed"
    assert "only one human author" in report.repo_notes
