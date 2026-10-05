"""Indexing endpoints: full snapshot + single file (async background)."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from app.dependencies import db_dep, settings_dep, tenant_ctx
from app.services import indexing_service

router = APIRouter(prefix="/repositories", tags=["indexing"])


class IndexSnapshotBody(BaseModel):
    files: list[dict] | None = None  # [{path, content}]
    root: str | None = None  # server-local path (local-dev mode)


class IndexFileBody(BaseModel):
    path: str
    content: str = ""


@router.post("/{repository_id}/index")
async def index_repo(repository_id: str, body: IndexSnapshotBody,
                     bg: BackgroundTasks, ctx=Depends(tenant_ctx),
                     db=Depends(db_dep), s=Depends(settings_dep),
                     background: bool = False):
    async def _run():
        return await indexing_service.index_snapshot(
            db, s, ctx["tenantId"], repository_id, files=body.files, root=body.root)
    if background:
        bg.add_task(_run)
        return {"status": "indexing", "repositoryId": repository_id}
    return await _run()


@router.post("/{repository_id}/index/file")
async def index_file(repository_id: str, body: IndexFileBody,
                     ctx=Depends(tenant_ctx), db=Depends(db_dep), s=Depends(settings_dep)):
    return await indexing_service.index_snapshot(
        db, s, ctx["tenantId"], repository_id,
        files=[{"path": body.path, "content": body.content}])
