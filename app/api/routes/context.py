"""Deep Agent context contract: POST /v1/context/select."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import db_dep, settings_dep
from app.models.search import ContextSelectRequest
from app.services import retrieval_service

router = APIRouter(tags=["context"])


@router.post("/context/select")
async def select_context(body: ContextSelectRequest,
                         db=Depends(db_dep), s=Depends(settings_dep)):
    # tenantId travels in the body per the Deep Agent contract; the tenant
    # guard still enforces its presence (never trust repo alone).
    return await retrieval_service.select_context(
        db, s, body.tenantId, body.repositoryId, body.query,
        limit=body.maxChunks * 4, filters={}, mode=body.mode,
        max_files=body.maxFiles, max_chunks=body.maxChunks, max_tokens=body.maxTokens,
        selected_files=body.selectedFiles, selected_symbols=body.selectedSymbols)
