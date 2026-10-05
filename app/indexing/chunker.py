"""Semantic chunker: symbol-aware chunks, never naive fixed-size as primary."""
from __future__ import annotations

import hashlib

MAX_CHUNK_LINES = 120
MAX_CHUNK_CHARS = 6000


def _slice(content: str, start: int, end: int) -> str:
    lines = content.splitlines()
    return "\n".join(lines[max(0, start - 1):end])


def chunk_file(
    path: str, content: str, language: str, kind: str, symbols: list[dict],
    index_version: int = 0,
) -> list[dict]:
    """Return chunk dicts (without tenant/repo/file ids; caller fills those)."""
    lines = content.splitlines()
    n = len(lines)
    chunks: list[dict] = []

    def make(symbol_name, symbol_type, start, end, parent=""):
        text = _slice(content, start, end)[:MAX_CHUNK_CHARS]
        h = hashlib.sha256(f"{path}:{start}:{end}:{text}".encode()).hexdigest()
        chunks.append({
            "path": path, "language": language,
            "symbolName": symbol_name, "symbolType": symbol_type,
            "startLine": start, "endLine": end,
            "content": text,
            "skeleton": f"{symbol_type} {symbol_name}".strip(),
            "hash": h, "indexVersion": index_version,
            "metadata": {"kind": kind, "parent": parent},
        })

    if symbols:
        for s in sorted(symbols, key=lambda x: x["startLine"]):
            length = s["endLine"] - s["startLine"] + 1
            if length > MAX_CHUNK_LINES:
                # Split oversized symbol bodies into overlapping windows.
                start = s["startLine"]
                while start <= s["endLine"]:
                    end = min(start + MAX_CHUNK_LINES - 1, s["endLine"])
                    make(s["qualifiedName"], s["type"], start, end, s.get("parent", ""))
                    start = end - 10  # overlap keeps context
                    if end == s["endLine"]:
                        break
            else:
                make(s["qualifiedName"], s["type"], s["startLine"], s["endLine"],
                     s.get("parent", ""))
        # Cover module-level gaps (imports, top-level code) as module chunks.
        covered = sorted((c["startLine"], c["endLine"]) for c in chunks)
        cursor = 1
        for a, b in covered:
            if a - cursor >= 15:
                make("", "module", cursor, a - 1)
            cursor = max(cursor, b + 1)
        if n - cursor >= 15:
            make("", "module", cursor, n)
    else:
        # No symbols (config/docs/unknown): semantic-ish block split on blank lines.
        if kind in {"config", "docs"} or language in {"json", "yaml", "toml", "markdown"}:
            start = 1
            buf: list[str] = []
            for i, line in enumerate(lines, 1):
                buf.append(line)
                if (not line.strip() or i == n) and len(buf) >= 10:
                    make("", "block", start, i)
                    start, buf = i + 1, []
            if buf:
                make("", "block", start, n)
        else:
            start = 1
            while start <= max(n, 1):
                make("", "module", start, min(start + MAX_CHUNK_LINES - 1, max(n, 1)))
                start += MAX_CHUNK_LINES
    return chunks
