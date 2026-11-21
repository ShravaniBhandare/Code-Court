"""Lizard function metrics and quality curves."""

from dataclasses import dataclass

import lizard

from app.config import settings

COMPLEXITY_WEIGHT = 0.60
SIZE_WEIGHT = 0.25
PARAMETER_WEIGHT = 0.15


@dataclass(frozen=True)
class FunctionInfo:
    """Metrics reported for one function."""

    name: str
    start_line: int
    end_line: int
    nloc: int
    cyclomatic_complexity: int
    parameter_count: int


def analyze_source(path: str, source: str) -> list[FunctionInfo]:
    """Analyze source with Lizard, returning an empty list on unsupported input."""
    if len(source.encode("utf-8")) > settings.LIZARD_MAX_FILE_BYTES:
        return []
    try:
        result = lizard.analyze_file.analyze_source_code(path, source)
        return [
            FunctionInfo(
                name=function.name,
                start_line=function.start_line,
                end_line=function.end_line,
                nloc=function.nloc,
                cyclomatic_complexity=function.cyclomatic_complexity,
                parameter_count=function.parameter_count,
            )
            for function in result.function_list
        ]
    except Exception:
        return []


def complexity_score(cyclomatic_complexity: int) -> float:
    """Score cyclomatic complexity on the configured 0-to-1 curve."""
    if cyclomatic_complexity <= 1:
        value = 0.30
    elif cyclomatic_complexity == 2:
        value = 0.65
    elif cyclomatic_complexity <= 15:
        value = 1.0
    elif cyclomatic_complexity <= 39:
        value = 1.0 - (cyclomatic_complexity - 15) * (0.8 / 24)
    else:
        value = 0.2
    return round(value, 4)


def size_score(nloc: int) -> float:
    """Score function size on the configured 0-to-1 curve."""
    if nloc <= 40:
        value = 1.0
    elif nloc <= 150:
        value = 1.0 - (nloc - 40) * (0.7 / 110)
    else:
        value = 0.3
    return round(value, 4)


def params_score(parameter_count: int) -> float:
    """Score function parameter count on the configured 0-to-1 curve."""
    if parameter_count <= 4:
        value = 1.0
    elif parameter_count <= 8:
        value = 1.0 - (parameter_count - 4) * (0.5 / 4)
    else:
        value = 0.4
    return round(value, 4)


def function_quality(function: FunctionInfo) -> float:
    """Return the weighted quality score for one function."""
    value = (
        COMPLEXITY_WEIGHT * complexity_score(function.cyclomatic_complexity)
        + SIZE_WEIGHT * size_score(function.nloc)
        + PARAMETER_WEIGHT * params_score(function.parameter_count)
    )
    return round(value, 4)
