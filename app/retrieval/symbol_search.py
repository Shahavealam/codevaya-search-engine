"""Symbol + dependency retrieval (exact-match friendly, cheap, high precision)."""
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import collections as C


async def symbol_search(
    db: AsyncIOMotorDatabase, tenant_id: str, repo_id: str, query: str, limit: int = 20,
) -> list[dict]:
    toks = [t for t in query.replace(".", " ").replace("(", " ").split() if len(t) > 2]
    if not toks:
        return []
    ors = []
    for t in toks[:8]:
        rx = {"$regex": t, "$options": "i"}
        ors += [{"name": rx}, {"qualifiedName": rx}]
    cur = db[C.SYMBOLS].find({"tenantId": tenant_id, "repositoryId": repo_id, "$or": ors}).limit(limit * 2)
    syms = await cur.to_list(length=limit * 2)
    # Join to chunks: symbol body chunks are the retrievable unit.
    out = []
    for s in syms[:limit]:
        c = await db[C.CODE_CHUNKS].find_one(
            {"tenantId": tenant_id, "repositoryId": repo_id,
             "path": s["path"], "symbolName": s["qualifiedName"]},
            {"path": 1, "symbolName": 1, "startLine": 1, "endLine": 1, "content": 1, "language": 1},
        ) or await db[C.CODE_CHUNKS].find_one(
            {"tenantId": tenant_id, "repositoryId": repo_id, "path": s["path"]},
            {"path": 1, "symbolName": 1, "startLine": 1, "endLine": 1, "content": 1, "language": 1},
        )
        if c:
            c["symbolScore"] = 1.0 if query.lower() in s["qualifiedName"].lower() else 0.6
            c["symMatched"] = True
            c["symbolName"] = s["qualifiedName"]
            out.append(c)
    return out


async def dependency_expand(
    db: AsyncIOMotorDatabase, tenant_id: str, repo_id: str, paths: list[str], limit: int = 20,
) -> list[dict]:
    if not paths:
        return []
    cur = db[C.DEPENDENCIES].find({
        "tenantId": tenant_id, "repositoryId": repo_id,
        "$or": [{"sourceFile": {"$in": paths}}, {"targetFile": {"$in": paths}}],
    }).limit(limit * 2)
    edges = await cur.to_list(length=limit * 2)
    related = {e["sourceFile"] for e in edges} | {e["targetFile"] for e in edges} - set(paths)
    out = []
    for p in list(related)[:limit]:
        c = await db[C.CODE_CHUNKS].find_one(
            {"tenantId": tenant_id, "repositoryId": repo_id, "path": p},
            {"path": 1, "symbolName": 1, "startLine": 1, "endLine": 1, "content": 1, "language": 1},
        )
        if c:
            c["dependencyScore"] = 0.7
            c["reason"] = "dependency expansion"
            out.append(c)
    return out
