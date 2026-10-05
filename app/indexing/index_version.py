"""Index version tracking (monotonic per repository)."""
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import collections as C


async def bump(db: AsyncIOMotorDatabase, repo_id: str) -> int:
    repo = await db[C.REPOSITORIES].find_one_and_update(
        {"_id": repo_id}, {"$inc": {"indexVersion": 1}}, return_document=True
    )
    return int(repo.get("indexVersion", 1)) if repo else 1
