"""Symbol lookup endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.db import collections as C
from app.dependencies import db_dep, tenant_ctx

router = APIRouter(prefix="/repositories", tags=["symbols"])


@router.get("/{repository_id}/symbols")
async def list_symbols(repository_id: str, ctx=Depends(tenant_ctx), db=Depends(db_dep),
                        q: str = "", limit: int = 50):
    query: dict = {"tenantId": ctx["tenantId"], "repositoryId": repository_id}
    if q:
        query["$or"] = [{"name": {"$regex": q, "$options": "i"}},
                        {"qualifiedName": {"$regex": q, "$options": "i"}}]
    cur = db[C.SYMBOLS].find(query).limit(limit)
    out = []
    async for d in cur:
        d.pop("_id", None)
        out.append(d)
    return out


@router.get("/{repository_id}/symbols/{qualified_name:path}")
async def get_symbol(repository_id: str, qualified_name: str,
                     ctx=Depends(tenant_ctx), db=Depends(db_dep)):
    doc = await db[C.SYMBOLS].find_one({
        "tenantId": ctx["tenantId"], "repositoryId": repository_id,
        "qualifiedName": qualified_name})
    if not doc:
        raise HTTPException(status_code=404, detail="Symbol not found")
    doc.pop("_id", None)
    # Attach body chunk.
    chunk = await db[C.CODE_CHUNKS].find_one({
        "tenantId": ctx["tenantId"], "repositoryId": repository_id,
        "path": doc["path"], "symbolName": qualified_name})
    if chunk:
        doc["content"] = chunk.get("content", "")
    return doc
