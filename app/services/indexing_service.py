"""Indexing orchestration: scan -> diff -> parse -> chunk -> embed -> upsert."""
from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import Settings
from app.db import collections as C
from app.indexing import chunker, dependency_indexer, embedding_indexer, lexical_indexer
from app.indexing import index_version as iv
from app.ingestion import incremental_indexer
from app.ingestion.repository_scanner import scan_directory, scan_snapshot
from app.parsing import import_extractor, skeleton_extractor, symbol_extractor
from app.security import secret_redactor


async def _parse_file(f: dict) -> dict:
    content = f.get("content", "")
    if secret_redactor.looks_like_secret_file(f["path"]):
        return {"ignored": True}
    content, _ = secret_redactor.redact(content)
    imports, exports = import_extractor.extract(f["path"], content, f.get("language", "unknown"))
    symbols = symbol_extractor.parse_symbols(f["path"], content, f.get("language", "unknown"))
    skeleton = skeleton_extractor.build_skeleton(f["path"], symbols, imports, exports)
    return {"content": content, "imports": imports, "exports": exports,
            "symbols": symbols, "skeleton": skeleton}


async def index_snapshot(
    db: AsyncIOMotorDatabase, settings: Settings, tenant_id: str, repo_id: str,
    files: list[dict] | None = None, root: str | None = None,
) -> dict:
    if files is not None:
        scanned = scan_snapshot(files)
    else:
        assert root is not None, "either files or root is required"
        scanned = await asyncio.to_thread(scan_directory, root)
    # Stored hashes for incremental diff.
    stored: dict[str, str] = {}
    cur = db[C.FILES].find({"tenantId": tenant_id, "repositoryId": repo_id}, {"path": 1, "sha256": 1})
    async for d in cur:
        stored[d["path"]] = d.get("sha256", "")
    plan = incremental_indexer.diff_files(scanned, stored)

    provider = embedding_indexer.build_provider(
        settings.embedding_provider, settings.openai_api_key, settings.openai_base_url,
        settings.embedding_model, settings.embedding_dims)

    now = datetime.now(UTC)
    changed = plan["changed"] + plan["new"]
    sem = asyncio.Semaphore(settings.index_workers)

    async def handle(f: dict):
        async with sem:
            return f, await _parse_file(f)

    parsed_list = await asyncio.gather(*(handle(f) for f in changed))
    file_imports: dict[str, list[str]] = {}
    all_chunks: list[dict] = []
    indexed_files = 0
    for f, parsed in parsed_list:
        if parsed.get("ignored"):
            await db[C.FILES].update_one(
                {"tenantId": tenant_id, "repositoryId": repo_id, "path": f["path"]},
                {"$set": {"ignored": True}}, upsert=True)
            continue
        file_imports[f["path"]] = parsed["imports"]
        chunks = chunker.chunk_file(
            f["path"], parsed["content"], f.get("language", "unknown"),
            f.get("kind", "code"), parsed["symbols"])
        for c in chunks:
            c.update({"tenantId": tenant_id, "repositoryId": repo_id})
        # Existing chunk hashes for this file (never re-embed unchanged).
        existing = set()
        cur2 = db[C.CODE_CHUNKS].find(
            {"tenantId": tenant_id, "repositoryId": repo_id, "path": f["path"]}, {"hash": 1})
        async for d in cur2:
            existing.add(d["hash"])
        await embedding_indexer.embed_new_chunks(
            provider, chunks, existing, settings.embedding_batch_size)
        # Chunks without embedding (unchanged) keep stored vectors: drop those w/o vec.
        fresh = [c for c in chunks if c.get("embedding") is not None]
        if fresh:
            await lexical_indexer.upsert_chunks(db, fresh)
        await lexical_indexer.delete_stale_chunks(
            db, tenant_id, repo_id, {c["hash"] for c in chunks}, f["path"])
        # Symbol docs.
        await db[C.SYMBOLS].delete_many(
            {"tenantId": tenant_id, "repositoryId": repo_id, "path": f["path"]})
        if parsed["symbols"]:
            await db[C.SYMBOLS].insert_many([
                {"tenantId": tenant_id, "repositoryId": repo_id, "fileId": "",
                 "path": f["path"], **s} for s in parsed["symbols"]
            ])
        await db[C.FILES].update_one(
            {"tenantId": tenant_id, "repositoryId": repo_id, "path": f["path"]},
            {"$set": {
                "tenantId": tenant_id, "repositoryId": repo_id, "path": f["path"],
                "language": f.get("language", "unknown"), "size": f.get("size", 0),
                "sha256": f["sha256"], "skeleton": parsed["skeleton"].model_dump(),
                "imports": parsed["imports"], "exports": parsed["exports"],
                "ignored": False, "updatedAt": now}},
            upsert=True)
        all_chunks.extend(fresh)
        indexed_files += 1

    # Deleted files cleanup.
    for d in plan["deleted"]:
        await db[C.FILES].delete_one({"tenantId": tenant_id, "repositoryId": repo_id, "path": d["path"]})
        await db[C.CODE_CHUNKS].delete_many(
            {"tenantId": tenant_id, "repositoryId": repo_id, "path": d["path"]})
        await db[C.SYMBOLS].delete_many(
            {"tenantId": tenant_id, "repositoryId": repo_id, "path": d["path"]})

    # Dependency graph refresh (cheap: only if something changed).
    if changed or plan["deleted"]:
        known: set[str] = set()
        cur3 = db[C.FILES].find({"tenantId": tenant_id, "repositoryId": repo_id}, {"path": 1})
        async for d in cur3:
            known.add(d["path"])
        imp_map: dict[str, list[str]] = dict(file_imports)
        cur4 = db[C.FILES].find({"tenantId": tenant_id, "repositoryId": repo_id},
                                {"path": 1, "imports": 1})
        async for d in cur4:
            imp_map.setdefault(d["path"], d.get("imports", []))
        edges = dependency_indexer.build_edges(tenant_id, repo_id, imp_map, known)
        await db[C.DEPENDENCIES].delete_many({"tenantId": tenant_id, "repositoryId": repo_id})
        if edges:
            await db[C.DEPENDENCIES].insert_many(edges)

    version = await iv.bump(db, repo_id)
    root_hash = hashlib.sha256("".join(sorted(stored)).encode()).hexdigest()[:16]
    await db[C.REPOSITORIES].update_one(
        {"_id": repo_id}, {"$set": {"rootHash": root_hash, "updatedAt": now}})

    return {
        "repositoryId": repo_id, "indexVersion": version,
        "indexedFiles": indexed_files,
        "unchangedFiles": len(plan["unchanged"]),
        "deletedFiles": len(plan["deleted"]),
        "chunks": len(all_chunks),
    }
