"""Lexical search: Atlas Search when available, BM25-lite fallback locally."""
from __future__ import annotations

import math
import re

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import collections as C
from app.indexing.lexical_indexer import atlas_lexical_pipeline

_TOKEN = re.compile(r"[A-Za-z_][\w.]*")


def _tokens(q: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(q)]


def bm25_lite_score(query: str, doc: dict) -> tuple[float, bool]:
    """Tiny BM25-ish scorer over content+symbol+path for local-dev fallback."""
    toks = _tokens(query)
    if not toks:
        return 0.0, False
    text = f"{doc.get('content','')} {doc.get('symbolName','')} {doc.get('path','')}".lower()
    terms = re.findall(r"[a-z_][\w.]*", text)
    if not terms:
        return 0.0, False
    tf = {t: terms.count(t) for t in set(toks)}
    matched = any(tf.get(t, 0) > 0 for t in toks)
    dl, avg = len(terms), 400.0
    score = 0.0
    for t in toks:
        f = tf.get(t, 0)
        if f:
            idf = 2.0 if len(t) > 4 else 1.0
            score += idf * (f * 2.2) / (f + 1.2 * (0.25 + 0.75 * dl / avg))
    # Exact identifier / path bonus: code search wins on exact matches.
    blob = text
    for t in set(toks):
        if t in blob:
            score += 0.8
    return score / (math.log2(len(toks) + 2) + 1), matched


async def search(
    db: AsyncIOMotorDatabase, tenant_id: str, repo_id: str, query: str,
    limit: int = 20, filters: dict | None = None, index_name: str = "code_chunks_lexical",
) -> list[dict]:
    filters = filters or {}
    # 1) Try Atlas Search.
    try:
        pipe = atlas_lexical_pipeline(index_name, query, tenant_id, repo_id, limit * 2, filters)
        agg_cur = db[C.CODE_CHUNKS].aggregate(pipe)
        docs = await agg_cur.to_list(length=limit * 2)
        if docs:
            for d in docs:
                d["lexicalScore"] = float(d.pop("score", 0.0))
                d["lexMatched"] = True
            return docs[:limit]
    except Exception:
        pass
    # 2) Local fallback: fetch projected chunks, score in Python.
    q: dict = {"tenantId": tenant_id, "repositoryId": repo_id}
    if filters.get("language"):
        q["language"] = filters["language"]
    if filters.get("pathPrefix"):
        q["path"] = {"$regex": f"^{filters['pathPrefix']}"}
    find_cur = db[C.CODE_CHUNKS].find(
        q, {"path": 1, "symbolName": 1, "startLine": 1, "endLine": 1, "content": 1, "language": 1}
    )
    docs = await find_cur.to_list(length=2000)
    scored = []
    for d in docs:
        s, matched = bm25_lite_score(query, d)
        if matched:
            d["lexicalScore"], d["lexMatched"] = s, True
            scored.append(d)
    return sorted(scored, key=lambda d: d["lexicalScore"], reverse=True)[:limit]
