"""Token estimation + context selection under maxFiles/maxChunks/maxTokens."""
from __future__ import annotations

from app.models.search import SearchHit

CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text) // CHARS_PER_TOKEN)


def enrich(hit: dict) -> SearchHit:
    content = hit.get("content", "")
    return SearchHit(
        path=hit.get("path", ""),
        symbol=hit.get("symbolName") or hit.get("symbol", ""),
        startLine=hit.get("startLine", 1),
        endLine=hit.get("endLine", 1),
        score=round(float(hit.get("score", hit.get("rrfScore", 0.0))), 4),
        reason=hit.get("reason", ""),
        content=content,
        charCount=len(content),
        tokenEstimate=estimate_tokens(content),
    )


def select(
    ranked: list[dict],
    max_files: int = 10, max_chunks: int = 8, max_tokens: int = 6000,
    user_files: list[str] | None = None, user_symbols: list[str] | None = None,
) -> tuple[list[SearchHit], int]:
    """Priority = .30 relevance + .20 dependency + .20 symbol + .15 recency + .15 user."""
    user_file_set = set(user_files or [])
    user_symbol_set = set(user_symbols or [])
    scored = []
    for d in ranked:
        user = 1.0 if (d.get("path") in user_file_set or d.get("symbolName") in user_symbol_set) else 0.0
        priority = (
            0.30 * float(d.get("score", d.get("rrfScore", 0.0)))
            + 0.20 * float(d.get("dependencyScore", 0.0))
            + 0.20 * float(d.get("symbolScore", 0.0))
            + 0.15 * float(d.get("recencyScore", 0.0))
            + 0.15 * user
        )
        scored.append((priority, d))
    scored.sort(key=lambda t: t[0], reverse=True)

    picked: list[SearchHit] = []
    files: set[str] = set()
    tokens = 0
    for _, d in scored:
        h = enrich(d)
        if len(picked) >= max_chunks or len(files | {h.path}) > max_files:
            if h.path not in files:
                continue
            if len(picked) >= max_chunks:
                break
        if tokens + h.tokenEstimate > max_tokens and picked:
            break
        picked.append(h)
        files.add(h.path)
        tokens += h.tokenEstimate
    return picked, tokens
