"""Search / context API contracts."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    language: str | None = None
    pathPrefix: str | None = None
    symbolType: str | None = None


class LexicalRequest(BaseModel):
    repositoryId: str
    query: str
    filters: SearchFilters = SearchFilters()
    limit: int = Field(default=20, le=100)


class SemanticRequest(BaseModel):
    repositoryId: str
    query: str
    filters: SearchFilters = SearchFilters()
    limit: int = Field(default=20, le=100)


class HybridRequest(BaseModel):
    repositoryId: str
    query: str
    filters: SearchFilters = SearchFilters()
    limit: int = Field(default=20, le=100)
    includeSymbols: bool = True
    includeDependencies: bool = True


class SearchHit(BaseModel):
    path: str
    symbol: str = ""
    startLine: int = 1
    endLine: int = 1
    score: float = 0.0
    reason: str = ""
    content: str = ""
    charCount: int = 0
    tokenEstimate: int = 0


class ContextSelectRequest(BaseModel):
    tenantId: str
    repositoryId: str
    query: str
    activeFile: str | None = None
    selectedFiles: list[str] = []
    selectedSymbols: list[str] = []
    maxTokens: int = 6000
    maxChunks: int = 8
    maxFiles: int = 10
    mode: str = "hybrid"  # lexical | semantic | hybrid


class ContextSelectResponse(BaseModel):
    repositoryId: str
    indexVersion: int = 0
    files: list[str] = []
    symbols: list[str] = []
    dependencies: list[dict] = []
    chunks: list[SearchHit] = []
    tokenEstimate: int = 0
