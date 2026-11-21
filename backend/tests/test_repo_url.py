"""Tests for GitHub repository reference parsing."""

import pytest

from app.core.errors import InvalidRepoURL
from app.core.repo_url import parse_repo_url


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://github.com/owner/repo", ("owner", "repo")),
        ("https://github.com/owner/repo/", ("owner", "repo")),
        ("https://github.com/owner/repo.git", ("owner", "repo")),
        ("http://github.com/owner/repo", ("owner", "repo")),
        ("https://www.github.com/owner/repo", ("owner", "repo")),
        ("https://github.com/owner/repo/tree/main/src", ("owner", "repo")),
        (" owner/repo ", ("owner", "repo")),
    ],
)
def test_parse_accepted_references(
    value: str, expected: tuple[str, str]
) -> None:
    """Accepted references return owner and repository names."""
    assert parse_repo_url(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "https://gitlab.com/owner/repo",
        "https://github.com/owner",
        "owner/repo with spaces",
        "owner/repo/name",
        "owner/repo!",
    ],
)
def test_parse_rejected_references(value: str) -> None:
    """Invalid references raise the domain exception."""
    with pytest.raises(InvalidRepoURL):
        parse_repo_url(value)
