"""Repository CRUD + file skeleton endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import db_dep, settings_dep, tenant_ctx
from app.models.repository import RepositoryCreate
from app.services import repository_service

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.post("")
async def create_repo(body: RepositoryCreate, ctx=Depends(tenant_ctx),
                      db=Depends(db_dep), s=Depends(settings_dep)):
    return await repository_service.create(
        db, ctx["tenantId"], body.workspaceId or ctx.get("workspaceId"),
        body.name, body.defaultBranch)


@router.get("")
async def list_repos(ctx=Depends(tenant_ctx), db=Depends(db_dep)):
    return await repository_service.list_for_tenant(db, ctx["tenantId"])


@router.get("/{repository_id}")
async def get_repo(repository_id: str, ctx=Depends(tenant_ctx), db=Depends(db_dep)):
    doc = await repository_service.get(db, ctx["tenantId"], repository_id)
    if not doc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Repository not found")
    return doc


@router.get("/{repository_id}/files")
async def list_files(repository_id: str, ctx=Depends(tenant_ctx), db=Depends(db_dep),
                     limit: int = 100):
    from app.db import collections as C
    cur = db[C.FILES].find(
        {"tenantId": ctx["tenantId"], "repositoryId": repository_id},
        {"content": 0}).limit(limit)
    out = []
    async for d in cur:
        d.pop("_id", None)
        d.pop("content", None)
        out.append(d)
    return out
