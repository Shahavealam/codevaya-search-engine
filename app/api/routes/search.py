"""Lexical / semantic / hybrid search endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import db_dep, settings_dep, tenant_ctx
from app.models.search import HybridRequest, LexicalRequest, SemanticRequest
from app.retrieval import context_selector
from app.services import retrieval_service

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/lexical")
async def lexical(body: LexicalRequest, ctx=Depends(tenant_ctx),
                  db=Depends(db_dep), s=Depends(settings_dep)):
    ranked = await retrieval_service.lexical(
        db, s, ctx["tenantId"], body.repositoryId, body.query,
        body.limit, body.filters.model_dump())
    chunks, _ = context_selector.select(ranked, max_chunks=body.limit)
    return {"results": [c.model_dump() for c in chunks]}


@router.post("/semantic")
async def semantic(body: SemanticRequest, ctx=Depends(tenant_ctx),
                   db=Depends(db_dep), s=Depends(settings_dep)):
    ranked = await retrieval_service.semantic(
        db, s, ctx["tenantId"], body.repositoryId, body.query,
        body.limit, body.filters.model_dump())
    chunks, _ = context_selector.select(ranked, max_chunks=body.limit)
    return {"results": [c.model_dump() for c in chunks]}


@router.post("/hybrid")
async def hybrid(body: HybridRequest, ctx=Depends(tenant_ctx),
                 db=Depends(db_dep), s=Depends(settings_dep)):
    ranked, lat = await retrieval_service.hybrid(
        db, s, ctx["tenantId"], body.repositoryId, body.query,
        body.limit, body.filters.model_dump(),
        body.includeSymbols, body.includeDependencies)
    chunks, _ = context_selector.select(ranked, max_chunks=body.limit)
    return {"results": [c.model_dump() for c in chunks], "latencyMs": lat}
