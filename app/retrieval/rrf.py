"""Reciprocal Rank Fusion baseline: RRF(d) = sum(1 / (k + rank_i(d)))."""
from __future__ import annotations


def fuse(ranked_lists: list[list[dict]], k: int = 60, key: str = "id") -> list[dict]:
    scores: dict[str, float] = {}
    docs: dict[str, dict] = {}
    for lst in ranked_lists:
        for rank, d in enumerate(lst, 1):
            did = str(d.get(key) or d.get("hash") or d.get("path"))
            scores[did] = scores.get(did, 0.0) + 1.0 / (k + rank)
            docs.setdefault(did, d)
    out = []
    for did, s in scores.items():
        d = dict(docs[did])
        d["rrfScore"] = s
        out.append(d)
    return sorted(out, key=lambda d: d["rrfScore"], reverse=True)
