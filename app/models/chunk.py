"""Code chunk models."""
from __future__ import annotations

from pydantic import BaseModel, Field


class CodeChunk(BaseModel):
    tenantId: str
    repositoryId: str
    fileId: str = ""
    path: str
    language: str = "unknown"
    symbolName: str = ""
    symbolType: str = ""
    startLine: int = 1
    endLine: int = 1
    content: str
    skeleton: str = ""
    hash: str = ""
    indexVersion: int = 0
    embedding: list[float] | None = Field(default=None, exclude=True)
    metadata: dict = {}
