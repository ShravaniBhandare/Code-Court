"""Per-commit touched-function quality analysis."""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.config import settings
from app.core.author_key import author_key, is_probably_bot
from app.core.file_filters import classify_path
from app.core.function_metrics import analyze_source, function_quality


@dataclass(frozen=True)
class FunctionTouch:
    """Quality metrics for a function touched by added lines."""

    path: str
    function_name: str
    cyclomatic_complexity: int
    nloc: int
    parameter_count: int
    added_lines_in_function: int
    weight: int
    quality: float


@dataclass(frozen=True)
class CommitQualityStats:
    """Quality metrics for one commit."""

    hash: str
    author_key: str
    author_name: str
    author_email: str
    is_bot: bool
    functions: tuple[FunctionTouch, ...]
    skipped_files: dict[str, int]


def _change_type(file: Any) -> str:
    """Return a stable PyDriller change type."""
    value = getattr(file, "change_type", "")
    return getattr(value, "name", str(value)).upper()


def analyze_commit_quality(commit: Any) -> CommitQualityStats:
    """Analyze functions containing meaningful added lines."""
    author = commit.author
    base = (commit.hash, author_key(author.name, author.email), author.name, author.email)
    if commit.merge:
        return CommitQualityStats(*base, is_probably_bot(author.name, author.email), (), {})

    touches: list[FunctionTouch] = []
    skipped: Counter[str] = Counter()
    for file in commit.modified_files:
        try:
            path = file.new_path or file.old_path or ""
            if classify_path(path) != "source":
                continue
            change_type = _change_type(file)
            if change_type == "RENAME" and not file.diff_parsed.get("added") and not file.diff_parsed.get("deleted"):
                skipped["pure rename"] += 1
                continue
            source = file.source_code
            if not source:
                skipped["no source"] += 1
                continue
            added = [
                (line_number, text)
                for line_number, text in file.diff_parsed.get("added", [])
                if text.strip()
            ]
            functions = analyze_source(path, source)
            if not functions:
                skipped["no functions found"] += 1
                continue
            assignments: dict[str, list[int]] = {function.name + str(index): [] for index, function in enumerate(functions)}
            for line_number, _ in added:
                candidates = [
                    (index, function)
                    for index, function in enumerate(functions)
                    if function.start_line <= line_number <= function.end_line
                ]
                if candidates:
                    index, _ = min(
                        candidates,
                        key=lambda pair: (
                            pair[1].end_line - pair[1].start_line,
                            pair[1].start_line,
                        ),
                    )
                    assignments[functions[index].name + str(index)].append(line_number)
            for index, function in enumerate(functions):
                line_numbers = assignments[function.name + str(index)]
                if len(line_numbers) < settings.MIN_ADDED_LINES_IN_FUNCTION:
                    continue
                touches.append(
                    FunctionTouch(
                        path=path,
                        function_name=function.name,
                        cyclomatic_complexity=function.cyclomatic_complexity,
                        nloc=function.nloc,
                        parameter_count=function.parameter_count,
                        added_lines_in_function=len(line_numbers),
                        weight=min(len(line_numbers), settings.FUNCTION_WEIGHT_CAP),
                        quality=function_quality(function),
                    )
                )
        except Exception as error:
            skipped[f"error: {type(error).__name__}"] += 1
    return CommitQualityStats(
        *base,
        is_probably_bot(author.name, author.email),
        tuple(touches),
        dict(skipped),
    )
