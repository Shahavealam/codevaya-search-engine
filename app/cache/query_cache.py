"""Query/context cache with tenant-isolated keys.

Key includes: tenantId + repositoryId + indexVersion + normalizedQuery +
filters + retrievalMode (per spec). Optional Redis tier; in-memory always on.
"""
from __future__ import annotations

import hashlib
import json
import time

_mem: dict[str, tuple[float, object]] = {}


def make_key(
    tenant_id: str, repository_id: str, index_version: int | str,
    query: str, filters: dict | None, mode: str,
) -> str:
    norm = " ".join(query.lower().split())
    raw = json.dumps({
        "t": tenant_id, "r": repository_id, "v": str(index_version),
        "q": norm, "f": filters or {}, "m": mode,
    }, sort_keys=True)
    return "q:" + hashlib.sha256(raw.encode()).hexdigest()


def get(key: str, ttl: int = 300):
    item = _mem.get(key)
    if not item:
        return None
    exp, val = item
    if time.time() > exp:
        _mem.pop(key, None)
        return None
    return val


def put(key: str, value: object, ttl: int = 300) -> None:
    _mem[key] = (time.time() + ttl, value)
    if len(_mem) > 2000:  # bounded
        _mem.pop(next(iter(_mem)))


def invalidate_repo(repository_id: str) -> None:
    # Values embed repo id only inside hashed key; simplest correct approach:
    # flush all (hot cache only, MongoDB is truth). Fine at this scale.
    _mem.clear()
