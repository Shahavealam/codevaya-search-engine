"""Repository CRUD + version lookup."""
from __future__ import annotations

from datetime import UTC, datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import collections as C


async def create(db: AsyncIOMotorDatabase, tenant_id: str, workspace_id: str | None, name: str,
                default_branch: str = "main") -> dict:
    now = datetime.now(UTC)
    doc = {"tenantId": tenant_id, "workspaceId": workspace_id, "name": name,
           "rootHash": "", "defaultBranch": default_branch, "indexVersion": 0,
           "createdAt": now, "updatedAt": now}
    res = await db[C.REPOSITORIES].insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    return doc


async def get(db: AsyncIOMotorDatabase, tenant_id: str, repo_id: str) -> dict | None:
    try:
        oid = ObjectId(repo_id)
        q: dict = {"$or": [{"_id": oid}, {"_id": repo_id}]}
    except Exception:
        q = {"_id": repo_id}
    doc = await db[C.REPOSITORIES].find_one(q)
    if doc and doc.get("tenantId") != tenant_id:
        return None  # cross-tenant access denied
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


async def list_for_tenant(db: AsyncIOMotorDatabase, tenant_id: str) -> list[dict]:
    cur = db[C.REPOSITORIES].find({"tenantId": tenant_id}).sort("updatedAt", -1).limit(100)
    out = []
    async for d in cur:
        d["_id"] = str(d["_id"])
        out.append(d)
    return out
