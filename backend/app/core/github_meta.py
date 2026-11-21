"""GitHub repository metadata retrieval."""

from typing import Any

import httpx

from app.config import settings
from app.core.errors import RateLimited, RepoNotFound, RepoTooLarge


def fetch_repo_meta(owner: str, repo: str) -> dict[str, Any]:
    """Fetch and validate metadata for a public GitHub repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"Accept": "application/vnd.github+json"}
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

    response = httpx.get(url, headers=headers, timeout=15)
    remaining = response.headers.get("x-ratelimit-remaining")
    if response.status_code in {403, 429} and remaining == "0":
        reset = response.headers.get("x-ratelimit-reset", "unknown")
        raise RateLimited(f"GitHub API rate limit exceeded; reset time: {reset}.")
    if response.status_code == 404:
        raise RepoNotFound(f"Repository {owner}/{repo} was not found or is private.")
    if response.status_code >= 400:
        raise RepoNotFound(f"Unable to access repository {owner}/{repo}.")

    data = response.json()
    if data.get("private") is True:
        raise RepoNotFound("Only public repositories are supported.")

    size_kb = int(data.get("size", 0))
    if size_kb > settings.MAX_REPO_SIZE_MB * 1024:
        raise RepoTooLarge(
            f"Repository {owner}/{repo} is {size_kb} KB, exceeding the "
            f"{settings.MAX_REPO_SIZE_MB} MB limit."
        )

    return {
        "full_name": data["full_name"],
        "default_branch": data["default_branch"],
        "size_kb": size_kb,
        "stargazers_count": data["stargazers_count"],
        "private": data["private"],
        "archived": data["archived"],
        "clone_url": data["clone_url"],
        "description": data["description"],
    }
