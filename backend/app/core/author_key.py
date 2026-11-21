"""Phase 1 grouping. Phase 2 replaces this with full identity resolution."""

_BOT_MARKERS = ("[bot]", "-bot", "dependabot", "renovate", "github-actions", "web-flow")


def author_key(author_name: str, author_email: str) -> str:
    """Return the temporary stable grouping key for an author."""
    email = author_email.strip().lower()
    return email or author_name.strip().lower()


def is_probably_bot(name: str, email: str) -> bool:
    """Return whether an author name or email resembles a bot identity."""
    value = f"{name} {email}".lower()
    return any(marker in value for marker in _BOT_MARKERS)
