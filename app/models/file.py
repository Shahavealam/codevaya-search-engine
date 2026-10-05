"""File / skeleton models."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ClassSkeleton(BaseModel):
    name: str
    methods: list[str] = []


class FileSkeleton(BaseModel):
    path: str
    imports: list[str] = []
    exports: list[str] = []
    classes: list[ClassSkeleton] = []
    interfaces: list[str] = []
    types: list[str] = []


class FileRecord(BaseModel):
    tenantId: str
    repositoryId: str
    path: str
    language: str = "unknown"
    size: int = 0
    sha256: str = ""
    skeleton: FileSkeleton | None = None
    imports: list[str] = []
    exports: list[str] = []
    ignored: bool = False
    indexVersion: int = 0
    modifiedAt: datetime | None = None
    updatedAt: datetime | None = None
