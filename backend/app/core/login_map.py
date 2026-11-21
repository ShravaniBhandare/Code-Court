"""Conservative GitHub-login to author-key mapping."""

import re
from collections.abc import Iterable


_NOREPLY = re.compile(r"^(?:\d+\+)?([^@]+)@users\.noreply\.github\.com$", re.I)


def build_login_map(
    commit_logins: dict[str, str], author_keys: Iterable[str]
) -> tuple[dict[str, str], list[str]]:
    """Map commit-email-derived logins without name or fuzzy matching."""
    by_email = {email.strip().lower(): login.lower() for email, login in commit_logins.items()}
    claims: dict[str, str] = {}
    unmatched: set[str] = set()
    for key in sorted(set(author_keys)):
        email = key.lower()
        login = by_email.get(email)
        if login is None:
            match = _NOREPLY.match(email)
            if match:
                candidate = match.group(1).lower()
                login = candidate
        if login is None:
            unmatched.add(key)
            continue
        prior = claims.get(login)
        if prior is None or key < prior:
            if prior is not None:
                unmatched.add(prior)
            claims[login] = key
        else:
            unmatched.add(key)
    return claims, sorted(unmatched)
