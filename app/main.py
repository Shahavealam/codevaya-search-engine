"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import context, health, indexing, repositories, search, symbols
from app.config import get_settings
from app.db import indexes, mongodb


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    # Validate embedding dims at startup (spec requirement).
    s.validate_vector_dims(s.embedding_dims)
    # Never block boot on Mongo (local-dev without DB must still serve /health
    # as degraded); index creation retries on first indexed write path too.
    try:
        import asyncio

        async def _init() -> None:
            db = mongodb.get_db(s.mongodb_uri, s.mongodb_db)
            await indexes.ensure_compound_indexes(db)

        await asyncio.wait_for(_init(), timeout=8)
    except Exception:
        pass  # local-dev without Mongo: API still boots (degraded /health)
    yield
    await mongodb.close()


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title=s.app_name, lifespan=lifespan)
    p = s.api_prefix
    app.include_router(health.router)  # GET /health (no prefix, per spec)
    app.include_router(repositories.router, prefix=p)
    app.include_router(indexing.router, prefix=p)
    app.include_router(search.router, prefix=p)
    app.include_router(symbols.router, prefix=p)
    app.include_router(context.router, prefix=p)
    return app


app = create_app()
