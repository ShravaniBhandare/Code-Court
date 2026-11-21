"""GitHub pull-request, review, issue, and commit-login collection."""

from dataclasses import dataclass
from datetime import datetime
from collections.abc import Callable
from typing import Any

from app.config import settings
from app.core.errors import GitHubAPIError, RateLimited, RepoNotFound
from app.core.github_client import GitHubClient


@dataclass(frozen=True)
class PullRequestInfo:
    number: int
    author_login: str
    created_at: datetime
    merged: bool
    is_bot_author: bool


@dataclass(frozen=True)
class ReviewEvent:
    pr_number: int
    reviewer_login: str
    state: str
    kind: str


@dataclass(frozen=True)
class IssueInfo:
    number: int
    author_login: str
    created_at: datetime
    is_bot_author: bool


@dataclass(frozen=True)
class IssueCommentEvent:
    issue_number: int
    author_login: str


@dataclass(frozen=True)
class ActivityData:
    prs: list[PullRequestInfo]
    review_events: list[ReviewEvent]
    issues: list[IssueInfo]
    issue_comments: list[IssueCommentEvent]
    commit_logins: dict[str, str]
    partial: bool
    warnings: list[str]
    requests_made: int


def _date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _login(user: dict[str, Any] | None) -> tuple[str, bool]:
    if not user:
        return "ghost", False
    login = str(user.get("login") or "ghost")
    return login, user.get("type") == "Bot" or login.lower().endswith("[bot]")


def _collect_step(
    name: str,
    action: Callable[[], None],
    warnings: list[str],
    progress: Callable[[str], None] | None,
) -> bool:
    if progress:
        progress(name)
    try:
        action()
    except (RateLimited, GitHubAPIError) as error:
        warnings.append(f"{name} collection stopped: {error}")
        return False
    return True


def collect_activity(
    owner: str,
    repo: str,
    since: datetime | None = None,
    client: GitHubClient | None = None,
    progress: Callable[[str], None] | None = None,
) -> ActivityData:
    """Collect GitHub activity, returning partial data on API failure."""
    own_client = client is None
    client = client or GitHubClient(settings.GITHUB_TOKEN)
    prs: list[PullRequestInfo] = []
    review_events: list[ReviewEvent] = []
    issues: list[IssueInfo] = []
    issue_comments: list[IssueCommentEvent] = []
    commit_logins: dict[str, str] = {}
    warnings: list[str] = []
    partial = False
    prefix = f"/repos/{owner}/{repo}"

    try:
        def pull_requests() -> None:
            nonlocal prs
            for item in client.paginate(
                f"{prefix}/pulls",
                {"state": "all", "sort": "created", "direction": "desc"},
                max_items=settings.MAX_PRS,
            ):
                created = _date(item["created_at"])
                if since and created < since:
                    continue
                login, bot = _login(item.get("user"))
                prs.append(PullRequestInfo(item["number"], login, created, item.get("merged_at") is not None, bot))

        if not _collect_step("PRs", pull_requests, warnings, progress):
            partial = True
            return ActivityData(prs, review_events, issues, issue_comments, commit_logins, partial, warnings, client.requests_made)

        def inline_comments() -> None:
            for item in client.paginate(f"{prefix}/pulls/comments"):
                created = _date(item["created_at"])
                if since and created < since:
                    continue
                login, _ = _login(item.get("user"))
                review_events.append(ReviewEvent(int(str(item["pull_request_url"]).rstrip("/").split("/")[-1]), login, "COMMENTED", "inline"))

        if not _collect_step("inline comments", inline_comments, warnings, progress):
            partial = True
            return ActivityData(prs, review_events, issues, issue_comments, commit_logins, partial, warnings, client.requests_made)

        def conversation_comments() -> None:
            for item in client.paginate(f"{prefix}/issues/comments"):
                created = _date(item["created_at"])
                if since and created < since:
                    continue
                login, _ = _login(item.get("user"))
                issue_comments.append(IssueCommentEvent(int(str(item["issue_url"]).rstrip("/").split("/")[-1]), login))

        if not _collect_step("conversation comments", conversation_comments, warnings, progress):
            partial = True
            return ActivityData(prs, review_events, issues, issue_comments, commit_logins, partial, warnings, client.requests_made)

        pr_numbers: set[int] = set()
        def load_issues() -> None:
            for item in client.paginate(f"{prefix}/issues", {"state": "all"}, max_items=settings.MAX_ISSUES):
                if "pull_request" in item:
                    pr_numbers.add(item["number"])
                    continue
                created = _date(item["created_at"])
                if since and created < since:
                    continue
                login, bot = _login(item.get("user"))
                issues.append(IssueInfo(item["number"], login, created, bot))
        if not _collect_step("issues", load_issues, warnings, progress):
            partial = True
            return ActivityData(prs, review_events, issues, issue_comments, commit_logins, partial, warnings, client.requests_made)
        if client.last_gone:
            warnings.append("issues are disabled for this repository")

        def submitted_reviews() -> None:
            if not settings.GITHUB_TOKEN:
                warnings.append("no GitHub token: skipping per-PR reviews to stay inside the 60 requests/hour limit")
                return
            for pr in prs[:settings.MAX_REVIEW_PRS]:
                for item in client.paginate(f"{prefix}/pulls/{pr.number}/reviews"):
                    state = str(item.get("state", "")).upper()
                    if state == "PENDING":
                        continue
                    login, _ = _login(item.get("user"))
                    review_events.append(ReviewEvent(pr.number, login, state, "review"))
        if not _collect_step("submitted reviews", submitted_reviews, warnings, progress):
            partial = True
            return ActivityData(prs, review_events, issues, issue_comments, commit_logins, partial, warnings, client.requests_made)

        def commit_authors() -> None:
            for item in client.paginate(f"{prefix}/commits", max_pages=settings.MAX_COMMIT_LOOKUP_PAGES):
                author = item.get("commit", {}).get("author") or {}
                user = item.get("author")
                if author.get("email") and user and user.get("login"):
                    commit_logins[str(author["email"]).lower()] = str(user["login"]).lower()
        if not _collect_step("commit authors", commit_authors, warnings, progress):
            partial = True
    except RepoNotFound:
        raise
    finally:
        if own_client:
            client.close()
    return ActivityData(prs, review_events, issues, issue_comments, commit_logins, partial, warnings, client.requests_made)
