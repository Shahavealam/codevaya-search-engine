"""Shared FastAPI dependencies: settings, db, tenant context."""
from __future__ import annotations

from fastapi import Header, HTTPException

from app.config import Settings, get_settings
from app.db import mongodb


def settings_dep() -> Settings:
    return get_settings()


def db_dep():
    s = get_settings()
    return mongodb.get_db(s.mongodb_uri, s.mongodb_db)


def tenant_ctx(
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
) -> dict[str, str | None]:
    # repositoryId travels in the body (per spec) but tenant/workspace come
    # from trusted headers; never trust a body-supplied tenantId alone.
    if not x_tenant_id:
        raise HTTPException(status_code=401, detail="Missing X-Tenant-ID")
    return {"tenantId": x_tenant_id, "workspaceId": x_workspace_id}
