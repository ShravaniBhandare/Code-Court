"""Fast classification of added source lines."""

from app.core.file_filters import LANGUAGE_BY_EXT

_C_FAMILY = {
    "c", "java", "kt", "js", "jsx", "ts", "tsx", "go", "rs", "swift", "scala",
    "php", "dart", "css", "scss",
}
_PUNCTUATION = set("{}()[];,")


def _toggle_delimited(line: str, state: bool, start: str, end: str) -> tuple[str, bool]:
    """Classify a delimited comment line and return its new state."""
    if state:
        if end in line:
            return "comment", False
        return "comment", True
    if line.startswith(start):
        remainder = line[len(start):]
        return "comment", end not in remainder
    return "", state


def classify_added_line(
    line: str, ext: str, in_block_comment: bool
) -> tuple[str, bool]:
    """Classify one added line and return its updated block-comment state."""
    stripped = line.strip()
    if not stripped:
        return "blank", in_block_comment
    family = LANGUAGE_BY_EXT.get(ext.lower(), "")

    if family in _C_FAMILY:
        category, state = _toggle_delimited(stripped, in_block_comment, "/*", "*/")
        if category:
            return category, state
        if stripped.startswith(("//", "*/")) or stripped == "*":
            return "comment", in_block_comment
        if "/*" in stripped:
            return "meaningful", "*/" not in stripped.split("/*", 1)[1]
        if stripped.startswith(("#include", "#define")):
            return "import", in_block_comment
        if stripped.startswith("import ") or stripped.startswith("package "):
            return "import", in_block_comment
        if family == "c" and stripped.startswith("using ") and stripped.endswith(";"):
            return "import", in_block_comment
        if stripped.startswith("use ") and stripped.endswith(";"):
            return "import", in_block_comment
    elif family == "hash":
        if stripped.startswith("#!") or stripped.startswith("#include"):
            return "meaningful" if stripped.startswith("#!") else "import", in_block_comment
        if in_block_comment:
            if '"""' in stripped:
                return "comment", False
            return "comment", True
        if stripped.startswith('"""') or stripped.startswith("'''"):
            delimiter = stripped[:3]
            return "comment", delimiter not in stripped[3:]
        if stripped.startswith("#"):
            return "comment", in_block_comment
        if stripped.startswith("import ") or (
            stripped.startswith("from ") and " import " in stripped
        ):
            return "import", in_block_comment
    elif family in {"sql", "lua"}:
        if stripped.startswith("--"):
            return "comment", in_block_comment
    elif family == "html":
        category, state = _toggle_delimited(stripped, in_block_comment, "<!--", "-->")
        if category:
            return category, state

    if stripped.startswith("require(") or (
        "=" in stripped and "require(" in stripped and stripped.endswith(")")
    ):
        return "import", in_block_comment
    if stripped.startswith(("import ", "package ")) and family in {"c", "c"}:
        return "import", in_block_comment
    if stripped and all(character in _PUNCTUATION or character.isspace() for character in stripped):
        return "punctuation", in_block_comment
    return "meaningful", in_block_comment
