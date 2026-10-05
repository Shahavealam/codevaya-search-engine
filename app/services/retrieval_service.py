"""Retrieval orchestration: hybrid + context selection + event logging + cache."""
from __future__ import annotations

import time
from datetime import UTC, datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.cache import context_cache, query_cache
from app.config import Settings
from app.db import collections as C
from app.indexing.embedding_indexer import build_provider
from app.retrieval import context_selector, hybrid_search, lexical_search, vector_search


async def _repo_version(db: AsyncIOMotorDatabase, repo_id: str) -> int:
    try:
        from bson import ObjectId
        doc = await db[C.REPOSITORIES].find_one({"_id": ObjectId(repo_id)})
    except Exception:
        doc = await db[C.REPOSITORIES].find_one({"_id": repo_id})
    return int((doc or {}).get("indexVersion", 0))


async def _log(db: AsyncIOMotorDatabase, tenant_id: str, repo_id: str, query: str,
               n: int, latency_ms: float, hit: bool) -> None:
    try:
        await db[C.SEARCH_EVENTS].insert_one({
            "tenantId": tenant_id, "repositoryId": repo_id, "query": query[:500],
            "filters": {}, "resultCount": n, "latencyMs": latency_ms,
            "cacheHit": hit, "createdAt": datetime.now(UTC)})
    except Exception:
        pass


async def lexical(db: AsyncIOMotorDatabase, s: Settings, tenant_id: str, repo_id: str,
                  query: str, limit: int, filters: dict) -> list[dict]:
    return await lexical_search.search(db, tenant_id, repo_id, query, limit, filters,
                                       s.atlas_search_index)


async def semantic(db: AsyncIOMotorDatabase, s: Settings, tenant_id: str, repo_id: str,
                   query: str, limit: int, filters: dict) -> list[dict]:
    provider = build_provider(s.embedding_provider, s.openai_api_key, s.openai_base_url,
                              s.embedding_model, s.embedding_dims)
    vec = (await provider.embed([query]))[0]
    return await vector_search.search(db, vec, tenant_id, repo_id, limit, filters,
                                      s.atlas_vector_index, s.atlas_vector_field)


async def hybrid(db: AsyncIOMotorDatabase, s: Settings, tenant_id: str, repo_id: str,
                 query: str, limit: int, filters: dict,
                 include_symbols: bool = True, include_deps: bool = True) -> tuple[list[dict], dict]:
    version = await _repo_version(db, repo_id)
    key = query_cache.make_key(tenant_id, repo_id, version, query, filters, "hybrid")
    if cached := query_cache.get(key, s.cache_ttl_seconds):
        return cached[0], {**cached[1], "cacheHit": True}
    provider = build_provider(s.embedding_provider, s.openai_api_key, s.openai_base_url,
                              s.embedding_model, s.embedding_dims)
    ranked, lat = await hybrid_search.hybrid(
        db, s, provider, tenant_id, repo_id, query, limit, filters,
        include_symbols, include_deps)
    query_cache.put(key, (ranked, lat), s.cache_ttl_seconds)
    await _log(db, tenant_id, repo_id, query, len(ranked), lat.get("totalMs", 0.0), False)
    return ranked, lat


async def select_context(db: AsyncIOMotorDatabase, s: Settings, tenant_id: str, repo_id: str,
                         query: str, limit: int, filters: dict, mode: str,
                         max_files: int, max_chunks: int, max_tokens: int,
                         selected_files: list[str], selected_symbols: list[str],
                         include_symbols: bool = True, include_deps: bool = True) -> dict:
    version = await _repo_version(db, repo_id)
    key = context_cache.make_key(tenant_id, repo_id, version, query,
                                 {**filters, "mode": mode}, "context")
    if cached := context_cache.get(key, s.cache_ttl_seconds):
        return {**cached, "cacheHit": True}
    t0 = time.perf_counter()
    if mode == "lexical":
        ranked = await lexical(db, s, tenant_id, repo_id, query, limit, filters)
        lat = {"totalMs": (time.perf_counter() - t0) * 1000}
    elif mode == "semantic":
        ranked = await semantic(db, s, tenant_id, repo_id, query, limit, filters)
        lat = {"totalMs": (time.perf_counter() - t0) * 1000}
    else:
        ranked, lat = await hybrid(db, s, tenant_id, repo_id, query, limit, filters,
                                   include_symbols, include_deps)
    chunks, tokens = context_selector.select(
        ranked, max_files, max_chunks, max_tokens, selected_files, selected_symbols)
    files = sorted({c.path for c in chunks})
    symbols = sorted({c.symbol for c in chunks if c.symbol})
    dep_edges: list[dict] = []
    if include_deps and files:
        cur = db[C.DEPENDENCIES].find(
            {"tenantId": tenant_id, "repositoryId": repo_id,
             "$or": [{"sourceFile": {"$in": files}}, {"targetFile": {"$in": files}}]}).limit(50)
        dep_edges = await cur.to_list(length=50)
        for e in dep_edges:
            e.pop("_id", None)
    resp = {"repositoryId": repo_id, "indexVersion": version,
            "files": files, "symbols": symbols, "dependencies": dep_edges,
            "chunks": [c.model_dump() for c in chunks],
            "tokenEstimate": tokens, "latencyMs": lat.get("totalMs", 0.0)}
    context_cache.put(key, resp, s.cache_ttl_seconds)
    return resp
