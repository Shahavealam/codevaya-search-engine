"""Health probes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.db import collections as C
from app.dependencies import db_dep, settings_dep

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db=Depends(db_dep), s=Depends(settings_dep)):
    mongo = "down"
    try:
        await db[C.REPOSITORIES].estimated_document_count()
        mongo = "up"
    except Exception:
        pass
    try:
        s.validate_vector_dims(s.embedding_dims)
        dims_ok = True
    except ValueError:
        dims_ok = False
    return {"status": "ok" if mongo == "up" else "degraded",
            "mongo": mongo, "embeddingModel": s.embedding_model,
            "embeddingDims": s.embedding_dims, "dimsOk": dims_ok,
            "atlasSearchIndex": s.atlas_search_index,
            "atlasVectorIndex": s.atlas_vector_index}
