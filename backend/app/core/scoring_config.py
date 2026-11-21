"""Configuration and scaling helpers for contribution scoring."""

import json
from dataclasses import dataclass
from math import isfinite, log1p, sqrt
from pathlib import Path

SIGNALS = ("work", "survival", "ownership", "review", "issues", "consistency")
DEFAULT_WEIGHTS = {
    "work": 0.45,
    "survival": 0.25,
    "ownership": 0.05,
    "review": 0.12,
    "issues": 0.06,
    "consistency": 0.07,
}
SCALING_MODES = ("log", "sqrt", "linear")


@dataclass(frozen=True)
class ScoringConfig:
    """Validated scoring configuration."""

    weights: dict[str, float]
    scaling: str
    min_penalty_multiplier: float = 0.5


def _validate_weights(weights: dict[str, object]) -> dict[str, float]:
    result = dict(DEFAULT_WEIGHTS)
    for name, value in weights.items():
        if name not in SIGNALS:
            raise ValueError(f"unknown signal name: {name}")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            raise ValueError(f"weight for {name} must be a finite number")
        if value < 0:
            raise ValueError(f"weight for {name} cannot be negative")
        result[name] = float(value)
    if not any(result.values()):
        raise ValueError("at least one scoring weight must be greater than zero")
    return result


def make_config(weights: dict | None = None, scaling: str = "log") -> ScoringConfig:
    """Create a validated scoring configuration."""
    if scaling not in SCALING_MODES:
        raise ValueError(f"unknown scaling mode: {scaling}")
    if weights is not None and not isinstance(weights, dict):
        raise ValueError("weights must be an object")
    return ScoringConfig(_validate_weights(weights or {}), scaling)


def load_config(path: Path) -> ScoringConfig:
    """Load a scoring configuration from JSON."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"could not read scoring config {path}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("scoring config must be a JSON object")
    unknown = set(payload) - {"weights", "scaling"}
    if unknown:
        raise ValueError(f"unknown scoring config keys: {', '.join(sorted(unknown))}")
    weights = payload.get("weights")
    if weights is not None and not isinstance(weights, dict):
        raise ValueError("scoring config weights must be an object")
    scaling = payload.get("scaling", "log")
    if not isinstance(scaling, str):
        raise ValueError("scoring config scaling must be a string")
    return make_config(weights, scaling)


def scale_value(value: float, max_value: float, mode: str) -> float:
    """Scale a positive value to the inclusive range 0..1."""
    if mode not in SCALING_MODES:
        raise ValueError(f"unknown scaling mode: {mode}")
    if max_value <= 0 or value <= 0:
        return 0.0
    if mode == "log":
        scaled = log1p(value) / log1p(max_value)
    elif mode == "sqrt":
        scaled = sqrt(value) / sqrt(max_value)
    else:
        scaled = value / max_value
    return max(0.0, min(1.0, scaled))
