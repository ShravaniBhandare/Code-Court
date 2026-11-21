"""Normalised review and issue activity signals."""

from collections import defaultdict
from dataclasses import dataclass

from app.config import settings
from app.core.activity import ActivityData
from app.core.scoring_config import scale_value


@dataclass(frozen=True)
class ActivityStats:
    """Raw activity totals for one mapped author."""

    prs_reviewed: int
    reviews_submitted: int
    inline_comments: int
    pr_comments: int
    issues_opened: int
    issue_comments: int
    review_points: float
    issue_points: float


@dataclass(frozen=True)
class ActivitySignals:
    """Review/issues signal values and collection diagnostics."""

    review: dict[str, float] | None
    issues: dict[str, float] | None
    stats: dict[str, ActivityStats]
    dropped_reasons: dict[str, str]
    unmatched_logins: list[str]


def compute_activity_signals(
    activity: ActivityData,
    login_to_author: dict[str, str],
    human_author_keys: list[str],
    scaling: str = "log",
) -> ActivitySignals:
    """Compute review and issue values from activity attributed to humans."""
    pr_authors = {item.number: item.author_login.lower() for item in activity.prs}
    pr_bots = {item.number for item in activity.prs if item.is_bot_author}
    pr_numbers = set(pr_authors)
    issue_numbers = {item.number for item in activity.issues}
    totals = {
        key: {
            "prs_reviewed": set(),
            "reviews_submitted": 0,
            "inline_comments": 0,
            "pr_comments": 0,
            "issues_opened": 0,
            "issue_comments": 0,
            "review_points": 0.0,
            "issue_points": 0.0,
        }
        for key in human_author_keys
    }
    per_pr: dict[str, dict[int, dict[str, int | bool]]] = defaultdict(
        lambda: defaultdict(lambda: {"review": False, "inline": 0, "comment": 0})
    )
    per_issue: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    unmatched: set[str] = set()

    def mapped(login: str) -> str | None:
        key = login_to_author.get(login.lower())
        if key is None:
            unmatched.add(login.lower())
        return key

    for event in activity.review_events:
        if event.reviewer_login.lower().endswith("[bot]"):
            continue
        key = mapped(event.reviewer_login)
        if key is None or event.pr_number not in pr_authors or event.pr_number in pr_bots:
            continue
        if key == login_to_author.get(pr_authors[event.pr_number], ""):
            continue
        totals[key]["prs_reviewed"].add(event.pr_number)
        if event.kind == "review":
            per_pr[key][event.pr_number]["review"] = True
            totals[key]["reviews_submitted"] += 1
        elif event.kind == "inline":
            per_pr[key][event.pr_number]["inline"] += 1
            totals[key]["inline_comments"] += 1
        else:
            per_pr[key][event.pr_number]["comment"] += 1
            totals[key]["pr_comments"] += 1

    pr_comment_events = []
    for event in activity.issue_comments:
        if event.author_login.lower().endswith("[bot]"):
            continue
        key = mapped(event.author_login)
        if key is None:
            continue
        if event.issue_number in pr_numbers:
            if key != login_to_author.get(pr_authors[event.issue_number], ""):
                totals[key]["prs_reviewed"].add(event.issue_number)
                per_pr[key][event.issue_number]["comment"] += 1
                totals[key]["pr_comments"] += 1
        elif event.issue_number in issue_numbers:
            owner = next(item.author_login.lower() for item in activity.issues if item.number == event.issue_number)
            if key != login_to_author.get(owner, ""):
                per_issue[key][event.issue_number] += 1

    for issue in activity.issues:
        if issue.is_bot_author:
            continue
        key = mapped(issue.author_login)
        if key is not None:
            totals[key]["issues_opened"] += 1

    for item in totals.values():
        key = next(
            author for author, value in totals.items() if value is item
        )
        item["review_points"] = sum(
            (3 if counts["review"] else 0)
            + min(int(counts["inline"]), 5)
            + min(int(counts["comment"]), 2)
            for counts in per_pr[key].values()
        )
        key = next(author for author, value in totals.items() if value is item)
        item["issue_comments"] = sum(per_issue[key].values())
        item["issue_points"] = item["issues_opened"] * 2 + sum(
            min(count, 3) for count in per_issue[key].values()
        )

    max_review = max((item["review_points"] for item in totals.values()), default=0)
    max_issue = max((item["issue_points"] for item in totals.values()), default=0)
    review_reason = None
    issue_reason = None
    if len(activity.prs) < settings.MIN_PRS_FOR_REVIEW:
        review_reason = f"fewer than {settings.MIN_PRS_FOR_REVIEW} pull requests"
    elif max_review == 0:
        review_reason = "no review activity found"
    if len(activity.issues) < settings.MIN_ISSUES_FOR_SIGNAL:
        issue_reason = f"fewer than {settings.MIN_ISSUES_FOR_SIGNAL} issues"
    elif max_issue == 0:
        issue_reason = "no issue activity found"
    if activity.partial:
        if review_reason:
            review_reason += " (GitHub data incomplete)"
        if issue_reason:
            issue_reason += " (GitHub data incomplete)"
    dropped = {}
    if review_reason:
        dropped["review"] = review_reason
    if issue_reason:
        dropped["issues"] = issue_reason
    values: dict[str, dict[str, float]] = {}
    if not review_reason:
        values["review"] = {key: scale_value(item["review_points"], max_review, scaling) for key, item in totals.items()}
    if not issue_reason:
        values["issues"] = {key: scale_value(item["issue_points"], max_issue, scaling) for key, item in totals.items()}
    stats = {
        key: ActivityStats(
            len(item["prs_reviewed"]), item["reviews_submitted"], item["inline_comments"],
            item["pr_comments"], item["issues_opened"], item["issue_comments"],
            item["review_points"], item["issue_points"],
        )
        for key, item in totals.items()
    }
    return ActivitySignals(
        stats=stats,
        review=values.get("review"),
        issues=values.get("issues"),
        dropped_reasons=dropped,
        unmatched_logins=sorted(unmatched),
    )
