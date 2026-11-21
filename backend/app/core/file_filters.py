"""Classification rules for changed repository paths."""

from pathlib import PurePath

LANGUAGE_BY_EXT = {
    ".py": "hash", ".rb": "hash", ".sh": "hash", ".bash": "hash", ".r": "hash",
    ".c": "c", ".h": "c", ".cpp": "c", ".hpp": "c", ".cc": "c", ".cs": "c",
    ".java": "c", ".kt": "c", ".js": "c", ".jsx": "c", ".ts": "c", ".tsx": "c",
    ".go": "c", ".rs": "c", ".swift": "c", ".scala": "c", ".php": "c",
    ".dart": "c", ".css": "c", ".scss": "c", ".sql": "sql", ".lua": "lua",
    ".html": "html", ".vue": "html", ".svelte": "html",
}

_IGNORED_SEGMENTS = {
    "node_modules", "vendor", "third_party", "dist", "build", "out", "target",
    ".git", "__pycache__", "venv", ".venv", "env", "coverage", ".idea", ".vscode",
    "site-packages", "bower_components", "pods",
}
_LOCK_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "pipfile.lock", "composer.lock", "cargo.lock", "gemfile.lock", "go.sum",
    "gradle.lockfile",
}
_BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".pdf", ".zip", ".tar",
    ".gz", ".jar", ".exe", ".dll", ".so", ".class", ".pyc", ".woff", ".woff2",
    ".ttf", ".mp3", ".mp4",
}
_DATA_EXTENSIONS = {".csv", ".tsv", ".parquet", ".sqlite", ".db", ".bin", ".dat"}
_SOURCE_EXTENSIONS = set(LANGUAGE_BY_EXT) | {
    ".m", ".html", ".css", ".scss", ".vue", ".svelte",
}
_CONFIG_EXTENSIONS = {
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".xml", ".properties",
}


def classify_path(path: str) -> str:
    """Return source, docs, config, or ignored for a repository path."""
    normalized = path.replace("\\", "/").lower()
    parts = PurePath(normalized).parts
    name = parts[-1] if parts else ""
    suffix = PurePath(name).suffix
    if any(part in _IGNORED_SEGMENTS for part in parts) or "ipynb_checkpoints" in parts:
        return "ignored"
    if (
        name in _LOCK_FILES
        or name.endswith((".min.js", ".min.css", ".map", ".pb.go", ".snap", "_pb2.py"))
        or ".generated." in name
    ):
        return "ignored"
    if suffix in _BINARY_EXTENSIONS or suffix in _DATA_EXTENSIONS:
        return "ignored"
    if name in {"dockerfile", "makefile", ".gitignore", ".editorconfig", ".env.example"}:
        return "config"
    if normalized.startswith("docs/") or suffix in {".md", ".rst", ".txt", ".adoc"}:
        return "docs"
    if suffix in _CONFIG_EXTENSIONS:
        return "config"
    if suffix in _SOURCE_EXTENSIONS:
        return "source"
    return "ignored"
