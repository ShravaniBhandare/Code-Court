"""GitHub repository URL parsing."""

import re
from urllib.parse import urlparse

from app.core.errors import InvalidRepoURL

_NAME = r"[A-Za-z0-9_.-]+"
_SHORTHAND = re.compile(rf"^({_NAME})/({_NAME})$")


def parse_repo_url(text: str) -> tuple[str, str]:
    """Return the owner and repository name from a GitHub repository reference."""
    value = text.strip()
    if not value or any(character.isspace() for character in value):
        raise InvalidRepoURL("Repository reference must be a non-empty GitHub URL.")

    shorthand = _SHORTHAND.fullmatch(value)
    if shorthand:
        owner, repo = shorthand.groups()
    else:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or parsed.hostname not in {
            "github.com",
            "www.github.com",
        }:
            raise InvalidRepoURL("Repository URL must use github.com.")

        parts = parsed.path.strip("/").split("/")
        if len(parts) < 2 or not parts[0] or not parts[1]:
            raise InvalidRepoURL("Repository URL must include an owner and repository.")
        owner, repo = parts[:2]

        if repo.endswith(".git"):
            repo = repo[:-4]

    if not re.fullmatch(_NAME, owner) or not re.fullmatch(_NAME, repo):
        raise InvalidRepoURL("Owner and repository names contain invalid characters.")
    return owner, repo
