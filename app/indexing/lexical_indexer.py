"""Lexical index writes (documents) + Atlas Search query helper.

Writes are plain MongoDB upserts — Atlas Search indexes them automatically.
When Atlas Search is unavailable (local dev), retrieval falls back to
regex/BM25-lite scoring in `app/retrieval/lexical_search.py`.
"""
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import collections as C


async def upsert_chunks(db: AsyncIOMotorDatabase, chunks: list[dict]) -> int:
    n = 0
    for c in chunks:
        await db[C.CODE_CHUNKS].update_one(
            {"tenantId": c["tenantId"], "repositoryId": c["repositoryId"], "hash": c["hash"]},
            {"$set": c},
            upsert=True,
        )
        n += 1
    return n


async def delete_stale_chunks(
    db: AsyncIOMotorDatabase, tenant_id: str, repo_id: str, live_hashes: set[str], file_path: str
) -> int:
    res = await db[C.CODE_CHUNKS].delete_many({
        "tenantId": tenant_id, "repositoryId": repo_id, "path": file_path,
        "hash": {"$nin": list(live_hashes) or ["__none__"]},
    })
    return res.deleted_count


def atlas_lexical_pipeline(
    index_name: str, query: str, tenant_id: str, repo_id: str,
    limit: int, filters: dict | None = None,
) -> list[dict]:
    compound: dict = {
        "must": [{"text": {"query": query, "path": ["content", "symbolName", "path"]}}],
        "filter": [
            {"text": {"query": tenant_id, "path": "tenantId"}},
            {"text": {"query": repo_id, "path": "repositoryId"}},
        ],
    }
    if filters and filters.get("language"):
        compound["filter"].append({"text": {"query": filters["language"], "path": "language"}})
    return [
        {"$search": {"index": index_name, "compound": compound}},
        {"$limit": limit},
        {"$project": {
            "path": 1, "symbolName": 1, "startLine": 1, "endLine": 1,
            "content": 1, "language": 1, "score": {"$meta": "searchScore"},
        }},
    ]
