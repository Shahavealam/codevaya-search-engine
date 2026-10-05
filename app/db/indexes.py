"""MongoDB index management.

Regular compound indexes are created directly. Atlas Search / Vector Search
indexes live in Atlas (not creatable via createIndex); this module emits the
JSON definitions consumed by `scripts/create_atlas_indexes.py` and validates
embedding dimensions at startup.
"""
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import collections as C


async def ensure_compound_indexes(db: AsyncIOMotorDatabase) -> None:
    await db[C.REPOSITORIES].create_index([("tenantId", 1), ("workspaceId", 1)])
    await db[C.REPOSITORIES].create_index([("tenantId", 1), ("rootHash", 1)])
    await db[C.FILES].create_index([("tenantId", 1), ("repositoryId", 1), ("path", 1)], unique=True)
    await db[C.FILES].create_index([("tenantId", 1), ("repositoryId", 1), ("sha256", 1)])
    await db[C.CODE_CHUNKS].create_index([("tenantId", 1), ("repositoryId", 1), ("fileId", 1)])
    await db[C.CODE_CHUNKS].create_index([("tenantId", 1), ("repositoryId", 1), ("hash", 1)])
    await db[C.SYMBOLS].create_index([("tenantId", 1), ("repositoryId", 1), ("qualifiedName", 1)])
    await db[C.SYMBOLS].create_index([("tenantId", 1), ("repositoryId", 1), ("name", 1)])
    await db[C.DEPENDENCIES].create_index([("tenantId", 1), ("repositoryId", 1), ("sourceFile", 1)])
    await db[C.DEPENDENCIES].create_index([("tenantId", 1), ("repositoryId", 1), ("targetFile", 1)])
    await db[C.SEARCH_EVENTS].create_index([("tenantId", 1), ("createdAt", -1)])


def atlas_search_index_definition(index_name: str) -> dict:
    """Lexical Atlas Search index over chunk content + path + symbol."""
    return {
        "name": index_name,
        "definition": {
            "mappings": {
                "dynamic": False,
                "fields": {
                    "content": {"type": "string"},
                    "path": {"type": "string"},
                    "symbolName": {"type": "string"},
                    "language": {"type": "string"},
                    "tenantId": {"type": "string"},
                    "repositoryId": {"type": "string"},
                }
            }
        },
    }


def atlas_vector_index_definition(
    index_name: str, field: str = "embedding", dims: int = 1536
) -> dict:
    """Vector Search index over code_chunks.embedding (dimensions are config-driven)."""
    return {
        "name": index_name,
        "type": "vectorSearch",
        "definition": {
            "fields": [
                {
                    "type": "vector",
                    "path": field,
                    "numDimensions": dims,
                    "similarity": "cosine",
                },
                {"type": "filter", "path": "tenantId"},
                {"type": "filter", "path": "repositoryId"},
                {"type": "filter", "path": "language"},
            ]
        },
    }
