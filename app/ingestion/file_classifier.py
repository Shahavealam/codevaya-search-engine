"""File classification: language detection + binary/secret heuristics."""
from __future__ import annotations

EXT_LANGUAGE = {
    ".py": "python", ".js": "javascript", ".jsx": "javascript", ".ts": "typescript",
    ".tsx": "typescript", ".go": "go", ".rs": "rust", ".java": "java",
    ".kt": "kotlin", ".rb": "ruby", ".php": "php", ".c": "c", ".h": "c",
    ".cpp": "cpp", ".hpp": "cpp", ".cs": "csharp", ".swift": "swift",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
    ".md": "markdown", ".sql": "sql", ".sh": "shell", ".tf": "terraform",
    ".html": "html", ".css": "css",
}

# Config-like files get "configuration block" chunking.
CONFIG_NAMES = {"Dockerfile", "Makefile", "package.json", "pyproject.toml", "go.mod"}


def classify(path: str, size: int, head: bytes) -> dict:
    """Return {language, kind, binary} without trusting extensions blindly."""
    if b"\x00" in head:
        return {"language": "binary", "kind": "binary", "binary": True}
    ext = "." + path.rsplit(".", 1)[-1].lower() if "." in path.rsplit("/", 1)[-1] else ""
    name = path.rsplit("/", 1)[-1]
    language = EXT_LANGUAGE.get(ext, "unknown")
    kind = "code"
    if name in CONFIG_NAMES or language in {"json", "yaml", "toml"}:
        kind = "config"
    if language == "markdown":
        kind = "docs"
    if "test" in name.lower() or "/tests/" in path or "/test/" in path:
        kind = "test"
    return {"language": language, "kind": kind, "binary": False}
