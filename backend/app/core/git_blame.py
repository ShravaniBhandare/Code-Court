"""Git operations used by survival analysis."""

from dataclasses import dataclass
from pathlib import Path
import subprocess

from app.config import settings
from app.core.blame_parser import parse_line_porcelain
from app.core.errors import CodeCourtError
from app.core.file_filters import classify_path


class BlameError(CodeCourtError):
    """Raised when Git cannot produce blame output for a file."""

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"{path}: {reason}")


@dataclass(frozen=True)
class SourceFile:
    """A source blob present at HEAD."""

    path: str
    size_bytes: int


def _run_git(
    repo_path: Path, arguments: list[str], timeout: int | float
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_path), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def list_head_source_files(repo_path: Path) -> tuple[list[SourceFile], dict[str, int]]:
    """List source blobs tracked by HEAD."""
    result = _run_git(
        repo_path, ["ls-tree", "-r", "-l", "-z", "HEAD"], settings.BLAME_TIMEOUT_SEC
    )
    if result.returncode:
        raise BlameError("", result.stderr.strip() or "git ls-tree failed")
    files: list[SourceFile] = []
    for entry in result.stdout.split("\0"):
        if not entry or "\t" not in entry:
            continue
        metadata, path = entry.split("\t", 1)
        fields = metadata.split()
        if len(fields) != 4:
            continue
        mode, kind, _, size_text = fields
        if kind != "blob" or mode not in {"100644", "100755"}:
            continue
        try:
            size = int(size_text)
        except ValueError:
            continue
        if classify_path(path) == "source":
            files.append(SourceFile(path, size))
    files.sort(key=lambda item: item.path)
    return files, {
        "total_source_files": len(files),
        "total_source_bytes": sum(item.size_bytes for item in files),
    }


def select_files_for_blame(
    files: list[SourceFile],
) -> tuple[list[SourceFile], dict[str, int]]:
    """Apply size and file-count limits to source files."""
    skipped: dict[str, int] = {}
    eligible = []
    for item in files:
        if item.size_bytes > settings.MAX_BLAME_FILE_BYTES:
            skipped["too large"] = skipped.get("too large", 0) + 1
        else:
            eligible.append(item)
    eligible.sort(key=lambda item: (-item.size_bytes, item.path))
    selected = eligible[: settings.MAX_BLAME_FILES]
    if len(eligible) > len(selected):
        skipped["file cap"] = len(eligible) - len(selected)
    return sorted(selected, key=lambda item: item.path), skipped


def compute_coverage(selected: list[SourceFile], all_files: list[SourceFile]) -> float:
    """Return the selected source-byte fraction."""
    total = sum(item.size_bytes for item in all_files)
    return 1.0 if total == 0 else sum(item.size_bytes for item in selected) / total


def find_ignore_revs_file(repo_path: Path) -> Path | None:
    """Find the optional repository-local ignored-revisions file."""
    candidate = repo_path / ".git-blame-ignore-revs"
    return candidate if candidate.is_file() else None


def blame_file(
    repo_path: Path, path: str, ignore_revs_file: Path | None
) -> list[tuple[str, str]]:
    """Blame one path at HEAD, retrying without ignored revisions if unsupported."""
    base = ["blame", "--line-porcelain", "-w", "-M"]
    with_ignore = base + (
        ["--ignore-revs-file", str(ignore_revs_file)] if ignore_revs_file else []
    )
    with_ignore += ["HEAD", "--", path]
    commands = [with_ignore]
    if ignore_revs_file:
        commands.append(base + ["HEAD", "--", path])
    last_reason = "git blame failed"
    for index, command in enumerate(commands):
        try:
            result = _run_git(repo_path, command, settings.BLAME_TIMEOUT_SEC)
        except subprocess.TimeoutExpired:
            raise BlameError(path, "timeout") from None
        except Exception as error:
            raise BlameError(path, type(error).__name__) from error
        if result.returncode == 0:
            return parse_line_porcelain(result.stdout)
        last_reason = result.stderr.strip() or "git blame failed"
        retryable = any(
            phrase in last_reason.lower()
            for phrase in ("unknown option", "invalid rev", "invalid object")
        )
        if index == 0 and ignore_revs_file and retryable:
            continue
        break
    raise BlameError(path, last_reason)
