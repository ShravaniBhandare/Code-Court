"""Tests for added-line classification."""

from app.core.line_classifier import classify_added_line


def test_basic_line_categories() -> None:
    """Blank, comment, import, punctuation, and code lines are classified."""
    assert classify_added_line("   ", ".py", False)[0] == "blank"
    assert classify_added_line("// c", ".js", False)[0] == "comment"
    assert classify_added_line("# c", ".py", False)[0] == "comment"
    assert classify_added_line("import os", ".py", False)[0] == "import"
    assert classify_added_line("from a import b", ".py", False)[0] == "import"
    assert classify_added_line("#include <stdio.h>", ".c", False)[0] == "import"
    assert classify_added_line("use std::fmt;", ".rs", False)[0] == "import"
    assert classify_added_line("}", ".py", False)[0] == "punctuation"
    assert classify_added_line("});", ".js", False)[0] == "punctuation"
    assert classify_added_line("{", ".js", False)[0] == "punctuation"
    assert classify_added_line("return x + 1", ".py", False)[0] == "meaningful"
    assert classify_added_line("x = 5", ".py", False)[0] == "meaningful"
    assert classify_added_line("#!/usr/bin/env python", ".py", False)[0] == "meaningful"


def test_block_comment_state() -> None:
    """C-style and Python docstring blocks carry state between lines."""
    category, state = classify_added_line("/* start", ".js", False)
    assert (category, state) == ("comment", True)
    category, state = classify_added_line("middle", ".js", state)
    assert (category, state) == ("comment", True)
    assert classify_added_line("end */", ".js", state) == ("comment", False)

    category, state = classify_added_line('"""start', ".py", False)
    assert (category, state) == ("comment", True)
    assert classify_added_line("body", ".py", state) == ("comment", True)
    assert classify_added_line('"""', ".py", True) == ("comment", False)


def test_trailing_comment_is_code() -> None:
    """Code preceding a trailing comment remains meaningful."""
    assert classify_added_line("value = 1  # note", ".py", False)[0] == "meaningful"
