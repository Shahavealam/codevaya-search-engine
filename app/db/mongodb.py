"""Motor (async MongoDB) connection management."""
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_client: AsyncIOMotorClient | None = None


def get_client(mongodb_uri: str) -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(mongodb_uri, serverSelectionTimeoutMS=2000)
    return _client


def get_db(mongodb_uri: str, db_name: str) -> AsyncIOMotorDatabase:
    return get_client(mongodb_uri)[db_name]


async def close() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
