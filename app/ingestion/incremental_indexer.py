"""Incremental indexer: diff scanned files against stored sha256; only changed work proceeds."""
from __future__ import annotations


def diff_files(scanned: list[dict], stored: dict[str, str]) -> dict[str, list[dict]]:
    """stored: {path: sha256}. Returns {unchanged, changed, new, deleted}."""
    unchanged, changed, new = [], [], []
    seen = set()
    for f in scanned:
        if f.get("ignored"):
            continue
        seen.add(f["path"])
        old = stored.get(f["path"])
        if old is None:
            new.append(f)
        elif old == f["sha256"]:
            unchanged.append(f)
        else:
            changed.append(f)
    deleted = [{"path": p} for p in stored if p not in seen]
    return {"unchanged": unchanged, "changed": changed, "new": new, "deleted": deleted}
