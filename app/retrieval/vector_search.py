"""Vector search: Atlas Vector Search when available, cosine fallback locally."""
from __future__ import annotations

import math

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import collections as C


def cosine(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(x * x for x in a[:n])) or 1.0
    nb = math.sqrt(sum(x * x for x in b[:n])) or 1.0
    return dot / (na * nb)


async def search(
    db: AsyncIOMotorDatabase, query_vec: list[float], tenant_id: str, repo_id: str,
    limit: int = 20, filters: dict | None = None,
    index_name: str = "code_chunks_vector", field: str = "embedding",
) -> list[dict]:
    filters = filters or {}
    # 1) Try Atlas Vector Search.
    try:
        filt: dict = {"tenantId": tenant_id, "repositoryId": repo_id}
        if filters.get("language"):
            filt["language"] = filters["language"]
        pipe = [
            {"$vectorSearch": {
                "index": index_name, "path": field, "queryVector": query_vec,
                "numCandidates": max(limit * 10, 100), "limit": limit, "filter": filt,
            }},
            {"$project": {
                "path": 1, "symbolName": 1, "startLine": 1, "endLine": 1,
                "content": 1, "language": 1, "score": {"$meta": "vectorSearchScore"},
            }},
        ]
        docs = await db[C.CODE_CHUNKS].aggregate(pipe).to_list(length=limit)
        if docs:
            for d in docs:
                d["semanticScore"] = float(d.pop("score", 0.0))
            return docs
    except Exception:
        pass
    # 2) Local cosine fallback (projected fetch, Python-side scoring).
    q: dict = {"tenantId": tenant_id, "repositoryId": repo_id}
    if filters.get("language"):
        q["language"] = filters["language"]
    cur = db[C.CODE_CHUNKS].find(q, {
        "path": 1, "symbolName": 1, "startLine": 1, "endLine": 1, "content": 1,
        "language": 1, field: 1,
    })
    docs = await cur.to_list(length=2000)
    scored = []
    for d in docs:
        v = d.pop(field, None)
        if v:
            d["semanticScore"] = cosine(query_vec, v)
            scored.append(d)
    return sorted(scored, key=lambda d: d["semanticScore"], reverse=True)[:limit]
