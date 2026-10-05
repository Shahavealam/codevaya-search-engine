"""Tenant isolation guard: every query must carry tenant + repository scope."""
from __future__ import annotations

from fastapi import HTTPException


def enforce(tenant_id: str | None, repository_id: str | None) -> tuple[str, str]:
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Missing tenant scope")
    if not repository_id:
        raise HTTPException(status_code=400, detail="Missing repositoryId")
    return tenant_id, repository_id


def scoped_filter(tenant_id: str, repository_id: str, extra: dict | None = None) -> dict:
    q = {"tenantId": tenant_id, "repositoryId": repository_id}
    if extra:
        q.update(extra)
    return q
