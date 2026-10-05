"""Ignore rules: .gitignore + .aiignore + built-in secret/binary/build exclusions."""
from __future__ import annotations

from pathlib import Path

import pathspec

# Never index these regardless of ignore files.
ALWAYS_EXCLUDE_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", "target", ".next", ".turbo", "coverage", ".pytest_cache",
}
ALWAYS_EXCLUDE_SUFFIXES = {
    ".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe", ".o", ".a",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".tar", ".gz",
    ".mp4", ".mp3", ".woff", ".woff2", ".ttf", ".eot",
}
ALWAYS_EXCLUDE_FILES = {
    ".env", ".env.local", ".env.production",
    ".pem", ".key", ".p12", ".pfx", ".crt", ".cer",
    "credentials.json", "secrets.json", "id_rsa", "id_ed25519",
}


def load_spec(root: Path, filename: str) -> pathspec.PathSpec | None:
    p = root / filename
    if not p.is_file():
        return None
    try:
        return pathspec.PathSpec.from_lines("gitwildmatch", p.read_text().splitlines())
    except Exception:
        return None


def is_ignored(rel_path: str, git_spec, ai_spec) -> bool:
    rel = rel_path.replace("\\", "/")
    name = rel.rsplit("/", 1)[-1]
    if name in ALWAYS_EXCLUDE_FILES:
        return True
    parts = set(rel.split("/"))
    if parts & ALWAYS_EXCLUDE_DIRS:
        return True
    if any(rel.endswith(s) for s in ALWAYS_EXCLUDE_SUFFIXES):
        return True
    if git_spec and git_spec.match_file(rel):
        return True
    if ai_spec and ai_spec.match_file(rel):
        return True
    return False
