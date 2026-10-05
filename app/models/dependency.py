"""Dependency models."""
from __future__ import annotations

from pydantic import BaseModel


class Dependency(BaseModel):
    tenantId: str
    repositoryId: str
    sourceFile: str
    targetFile: str
    sourceSymbol: str = ""
    targetSymbol: str = ""
    type: str = "import"  # import | call | reference
    metadata: dict = {}
