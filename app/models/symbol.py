"""Symbol models."""
from __future__ import annotations

from pydantic import BaseModel


class Symbol(BaseModel):
    tenantId: str
    repositoryId: str
    fileId: str = ""
    path: str
    name: str
    qualifiedName: str
    type: str = "function"  # function | method | class | interface | type | variable
    signature: str = ""
    startLine: int = 1
    endLine: int = 1
    parent: str = ""
    exported: bool = False
    references: int = 0
    metadata: dict = {}
