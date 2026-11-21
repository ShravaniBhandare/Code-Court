"""Parser for Git's line-porcelain blame format."""

import re

_HEADER = re.compile(r"^[0-9a-f]{40} \d+ \d+(?: \d+)?$")


def parse_line_porcelain(text: str) -> list[tuple[str, str]]:
    """Return ``(commit_sha, content)`` pairs in file order."""
    result: list[tuple[str, str]] = []
    current_sha: str | None = None
    for raw_line in text.split("\n"):
        if raw_line.startswith("\t"):
            if current_sha is not None:
                result.append((current_sha, raw_line[1:]))
            continue
        if _HEADER.match(raw_line.rstrip("\r")):
            current_sha = raw_line[:40]
    return result
