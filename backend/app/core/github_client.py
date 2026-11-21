"""Small, testable GitHub REST client."""

from collections.abc import Callable
import time
from typing import Any
from urllib.parse import quote

import httpx

from app.config import settings
from app.core.errors import GitHubAPIError, RateLimited, RepoNotFound


class GitHubClient:
    """GitHub REST client with bounded retries and pagination."""

    def __init__(
        self,
        token: str = "",
        base_url: str | None = None,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "CodeCourt",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = client or httpx.Client(
            base_url=base_url or settings.GITHUB_API_BASE,
            headers=headers,
            timeout=settings.HTTP_TIMEOUT_SEC,
        )
        self._owned = client is None
        self._base_url = (base_url or settings.GITHUB_API_BASE).rstrip("/")
        self._sleep = sleep
        self.requests_made = 0
        self.rate_remaining: int | None = None
        self.last_gone = False

    def get_json(
        self, path: str, params: dict[str, Any] | None = None
    ) -> tuple[Any, httpx.Headers]:
        """Fetch JSON, applying the specified retry policy."""
        if path.startswith(("http://", "https://")):
            url = path
        else:
            url = self._base_url + "/" + "/".join(
                quote(part, safe="") for part in path.strip("/").split("/")
            )
        transport_attempts = 0
        secondary_retried = False
        while True:
            try:
                self.requests_made += 1
                response = self._client.get(url, params=params)
            except httpx.TransportError as error:
                if transport_attempts < 2:
                    self._sleep(2**transport_attempts)
                    transport_attempts += 1
                    continue
                raise GitHubAPIError("GitHub request failed after retries") from error
            remaining = response.headers.get("x-ratelimit-remaining")
            self.rate_remaining = int(remaining) if remaining and remaining.isdigit() else self.rate_remaining
            if response.status_code == 401:
                raise GitHubAPIError("GitHub rejected the token")
            if response.status_code == 404:
                raise RepoNotFound("GitHub repository or resource was not found")
            if response.status_code == 410:
                self.last_gone = True
                return [], response.headers
            if response.status_code in (403, 429):
                if remaining == "0":
                    reset = response.headers.get("x-ratelimit-reset", "unknown")
                    raise RateLimited(f"GitHub rate limit exhausted; reset at {reset}")
                retry_after = response.headers.get("retry-after")
                if retry_after and not secondary_retried:
                    try:
                        self._sleep(min(float(retry_after), 60))
                    except ValueError:
                        pass
                    secondary_retried = True
                    continue
                raise GitHubAPIError("GitHub request was rejected")
            if response.status_code >= 500:
                if transport_attempts < 2:
                    self._sleep(2**transport_attempts)
                    transport_attempts += 1
                    continue
                raise GitHubAPIError("GitHub server failed after retries")
            if response.is_error:
                raise GitHubAPIError(f"GitHub request failed with status {response.status_code}")
            return response.json(), response.headers

    def paginate(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        max_pages: int = settings.MAX_LIST_PAGES,
        max_items: int | None = None,
    ) -> list[Any]:
        """Collect paginated list results."""
        values: list[Any] = []
        current_path = path
        current_params = dict(params or {})
        current_params["per_page"] = 100
        for _ in range(max_pages):
            page, headers = self.get_json(current_path, current_params)
            if not isinstance(page, list):
                raise GitHubAPIError("GitHub pagination expected a list response")
            values.extend(page)
            if max_items is not None and len(values) >= max_items:
                return values[:max_items]
            if len(page) < 100:
                break
            next_url = _next_link(headers.get("link"))
            if not next_url:
                break
            current_path, current_params = next_url, {}
        return values[:max_items] if max_items is not None else values

    def close(self) -> None:
        if self._owned:
            self._client.close()

    def __enter__(self) -> "GitHubClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _next_link(link: str | None) -> str | None:
    if not link:
        return None
    for part in link.split(","):
        url, _, relation = part.partition(";")
        if 'rel="next"' in relation:
            return url.strip().strip("<>")
    return None
