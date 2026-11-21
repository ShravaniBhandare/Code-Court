"""Tests for line-porcelain parsing."""

from app.core.blame_parser import parse_line_porcelain


def test_parse_line_porcelain_preserves_content_and_shas() -> None:
    sha_a = "a" * 40
    sha_b = "b" * 40
    text = (
        f"{sha_a} 1 1 2\n"
        "author Alice\n"
        "summary first\n"
        "\tfirst\n"
        f"{sha_a} 2 2\n"
        "author Alice\n"
        "\tauthor Bob\n"
        f"{sha_b} 3 3\n"
        "boundary\n"
        "\t\n"
    )

    assert parse_line_porcelain(text) == [
        (sha_a, "first"),
        (sha_a, "author Bob"),
        (sha_b, ""),
    ]


def test_parse_line_porcelain_skips_garbage() -> None:
    assert parse_line_porcelain("garbage\nnot a header\n") == []
