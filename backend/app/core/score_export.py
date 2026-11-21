"""JSON export for score reports."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from app.core.scoring import ScoreReport
from app.core.anomalies import Anomaly


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    return value


def report_to_dict(report: ScoreReport, extras: dict | None = None) -> dict[str, Any]:
    """Convert a score report to JSON-serializable data."""
    result = _normalize(asdict(report))
    if extras:
        result.update(extras)
    return result


def anomalies_to_list(anomalies: list[Anomaly]) -> list[dict[str, Any]]:
    """Convert anomaly dataclasses to JSON-friendly dictionaries."""
    return [_normalize(asdict(item)) for item in anomalies]


def write_report_json(report: ScoreReport, path: Path, extras: dict | None = None) -> None:
    """Write an indented score report JSON file."""
    path.write_text(
        json.dumps(report_to_dict(report, extras), indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
