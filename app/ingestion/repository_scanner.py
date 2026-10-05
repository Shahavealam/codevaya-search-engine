"""Repository scanner: discover files on disk or from an uploaded snapshot."""
from __future__ import annotations

import hashlib
from pathlib import Path

from app.ingestion import ignore_rules
from app.ingestion.file_classifier import classify

MAX_FILE_BYTES = 1_000_000  # skip >1MB files (minimize tokens, avoid binaries)


def scan_directory(root: str | Path) -> list[dict]:
    root_p = Path(root)
    git_spec = ignore_rules.load_spec(root_p, ".gitignore")
    ai_spec = ignore_rules.load_spec(root_p, ".aiignore")
    out: list[dict] = []
    for p in sorted(root_p.rglob("*")):
        if not p.is_file() or p.is_symlink():
            continue
        rel = p.relative_to(root_p).as_posix()
        if ignore_rules.is_ignored(rel, git_spec, ai_spec):
            out.append({"path": rel, "ignored": True})
            continue
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if size > MAX_FILE_BYTES:
            out.append({"path": rel, "ignored": True, "reason": "too-large"})
            continue
        head = p.read_bytes()[:8192]
        cls = classify(rel, size, head)
        if cls["binary"]:
            out.append({"path": rel, "ignored": True, "reason": "binary"})
            continue
        content = p.read_text(encoding="utf-8", errors="ignore")
        sha = hashlib.sha256(content.encode()).hexdigest()
        out.append({
            "path": rel, "content": content, "sha256": sha,
            "size": size, "language": cls["language"], "kind": cls["kind"],
            "ignored": False,
        })
    return out


def scan_snapshot(files: list[dict]) -> list[dict]:
    """Normalize an uploaded snapshot: [{path, content}]. Applies ignore rules w/o disk."""
    git_spec = ai_spec = None
    by_path = {f["path"]: f.get("content", "") for f in files}
    gitignore = by_path.get(".gitignore", "")
    aiignore = by_path.get(".aiignore", "")
    import pathspec
    if gitignore:
        git_spec = pathspec.PathSpec.from_lines("gitwildmatch", gitignore.splitlines())
    if aiignore:
        ai_spec = pathspec.PathSpec.from_lines("gitwildmatch", aiignore.splitlines())
    out: list[dict] = []
    for f in files:
        rel = f["path"]
        if ignore_rules.is_ignored(rel, git_spec, ai_spec):
            out.append({"path": rel, "ignored": True})
            continue
        content = f.get("content", "")
        import hashlib
        out.append({
            "path": rel, "content": content,
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
            "size": len(content.encode()),
            "language": classify(rel, len(content), content[:100].encode())["language"],
            "kind": "code", "ignored": False,
        })
    return out
