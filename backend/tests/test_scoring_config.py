"""Tests for scoring configuration."""

import json
from pathlib import Path

import pytest

from app.core.scoring_config import (
    DEFAULT_WEIGHTS,
    SIGNALS,
    load_config,
    make_config,
    scale_value,
)


def test_default_config_and_overrides_do_not_mutate_input() -> None:
    overrides = {"work": 2}
    config = make_config(overrides, "linear")

    assert config.scaling == "linear"
    assert config.weights["work"] == 2
    assert overrides == {"work": 2}
    assert tuple(config.weights) == SIGNALS
    assert DEFAULT_WEIGHTS["work"] == 0.45


@pytest.mark.parametrize("mode", ["log", "sqrt", "linear"])
def test_scale_value(mode: str) -> None:
    assert scale_value(0, 10, mode) == 0.0
    assert 0.0 <= scale_value(5, 10, mode) <= 1.0
    assert scale_value(10, 10, mode) == 1.0


def test_invalid_config_and_json(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        make_config({"unknown": 1})
    with pytest.raises(ValueError):
        make_config({"work": -1})
    with pytest.raises(ValueError):
        make_config({"work": 0, "survival": 0, "ownership": 0, "review": 0, "issues": 0, "consistency": 0})
    with pytest.raises(ValueError):
        load_config(tmp_path / "missing.json")
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"bad": True}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(path)
