"""Clone and update cached repositories."""

import shutil
import subprocess
from pathlib import Path
import re

from app.config import settings
from app.core.errors import CloneFailed, InvalidRepoURL

_SAFE_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")


def _run_git(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a git command with the configured timeout."""
    try:
        result = subprocess.run(
            arguments,
            capture_output=True,
            text=True,
            timeout=settings.GIT_CLONE_TIMEOUT_SEC,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise CloneFailed(f"Git command timed out: {' '.join(arguments)}") from error
    if result.returncode != 0:
        detail = result.stderr.strip() or "no error details"
        raise CloneFailed(f"Git command failed: {detail}")
    return result


def ensure_clone(owner: str, repo: str, clone_url: str) -> Path:
    """Ensure a cached repository exists and is up to date."""
    if not _SAFE_NAME.fullmatch(owner) or not _SAFE_NAME.fullmatch(repo):
        raise InvalidRepoURL("Owner and repository names contain invalid characters.")

    cache_dir = Path(settings.CACHE_DIR).expanduser().resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    repo_path = (cache_dir / f"{owner}__{repo}").resolve()

    if repo_path.exists() and (repo_path / ".git").is_dir():
        _run_git(["git", "-C", str(repo_path), "fetch", "--quiet", "origin"])
        try:
            _run_git(["git", "-C", str(repo_path), "pull", "--ff-only", "--quiet"])
        except CloneFailed:
            shutil.rmtree(repo_path)
            _run_git(["git", "clone", "--quiet", clone_url, str(repo_path)])
    elif repo_path.exists():
        raise CloneFailed(f"Cache path exists but is not a Git repository: {repo_path}")
    else:
        _run_git(["git", "clone", "--quiet", clone_url, str(repo_path)])

    return repo_path


def get_head_sha(repo_path: Path) -> str:
    """Return the current HEAD SHA for a local repository."""
    return _run_git(["git", "-C", str(repo_path), "rev-parse", "HEAD"]).stdout.strip()


def get_remote_head_sha(clone_url: str) -> str:
    """Return the remote HEAD SHA without cloning the repository."""
    result = _run_git(["git", "ls-remote", clone_url, "HEAD"])
    value = result.stdout.strip().splitlines()
    if not value or not value[0].split():
        raise CloneFailed("Remote repository returned no HEAD")
    return value[0].split()[0]
