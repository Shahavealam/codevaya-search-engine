"""Repository models."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RepositoryCreate(BaseModel):
    tenantId: str
    workspaceId: str | None = None
    name: str
    defaultBranch: str = "main"


class Repository(BaseModel):
    id: str = Field(alias="_id", default="")
    tenantId: str
    workspaceId: str | None = None
    name: str
    rootHash: str = ""
    defaultBranch: str = "main"
    indexVersion: int = 0
    createdAt: datetime | None = None
    updatedAt: datetime | None = None

    model_config = {"populate_by_name": True}
