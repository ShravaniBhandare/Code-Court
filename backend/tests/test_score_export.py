"""Tests for score JSON export."""

import json

from app.core.score_export import report_to_dict, write_report_json
from app.core.scoring import compute_scores
from app.core.size_signal import AuthorSize


def test_score_export_is_json_serializable(tmp_path) -> None:
    size = AuthorSize("a", "A", "a@example.com", 1, 0, 0.0, 1, 1, 1, 0, 0, 0, 0.0)
    report = compute_scores([size], [], None)
    output = tmp_path / "score.json"
    write_report_json(report, output)

    assert json.loads(output.read_text(encoding="utf-8")) == report_to_dict(report)
