"""Hybrid retrieval: lexical + semantic + symbol + dependency -> normalize -> RRF -> rerank."""
from __future__ import annotations

import time

from app.config import Settings
from app.indexing.embedding_indexer import EmbeddingProvider
from app.retrieval import lexical_search, reranker, symbol_search, vector_search
from app.retrieval import rrf as rrf_mod


def _norm(docs: list[dict], field: str) -> None:
    mx = max((float(d.get(field, 0.0)) for d in docs), default=0.0)
    for d in docs:
        d[field] = float(d.get(field, 0.0)) / mx if mx > 0 else 0.0
        d.setdefault("lexicalScore", 0.0)
        d.setdefault("semanticScore", 0.0)
        d.setdefault("symbolScore", 0.0)
        d.setdefault("dependencyScore", 0.0)
        d.setdefault("recencyScore", 0.0)


def _key(d: dict) -> str:
    return f"{d.get('path','')}#{d.get('symbolName','')}#{d.get('startLine',0)}"


async def hybrid(
    db, settings: Settings, provider: EmbeddingProvider,
    tenant_id: str, repo_id: str, query: str,
    limit: int = 20, filters: dict | None = None,
    include_symbols: bool = True, include_dependencies: bool = True,
) -> tuple[list[dict], dict]:
    filters = filters or {}
    t0 = time.perf_counter()
    lat: dict[str, float] = {}

    t = time.perf_counter()
    lex = await lexical_search.search(
        db, tenant_id, repo_id, query, limit, filters, settings.atlas_search_index)
    lat["lexicalMs"] = (time.perf_counter() - t) * 1000

    t = time.perf_counter()
    vec = await provider.embed([query])
    lat["embeddingMs"] = (time.perf_counter() - t) * 1000

    t = time.perf_counter()
    sem = await vector_search.search(
        db, vec[0], tenant_id, repo_id, limit, filters,
        settings.atlas_vector_index, settings.atlas_vector_field)
    lat["vectorMs"] = (time.perf_counter() - t) * 1000

    sym: list[dict] = []
    if include_symbols:
        t = time.perf_counter()
        sym = await symbol_search.symbol_search(db, tenant_id, repo_id, query, limit)
        lat["symbolMs"] = (time.perf_counter() - t) * 1000

    _norm(lex, "lexicalScore")
    _norm(sem, "semanticScore")
    _norm(sym, "symbolScore")

    for d in lex:
        d["reason"] = "lexical match"
    for d in sem:
        d["reason"] = "semantic match"
    for d in sym:
        d["reason"] = "symbol match"

    fused = rrf_mod.fuse([lex, sem, sym], k=settings.rrf_k, key="__k__") if False else _fuse(
        [lex, sem, sym], settings.rrf_k)

    dep: list[dict] = []
    if include_dependencies and fused:
        t = time.perf_counter()
        top_paths = [d["path"] for d in fused[:5]]
        dep = await symbol_search.dependency_expand(db, tenant_id, repo_id, top_paths, limit)
        lat["dependencyMs"] = (time.perf_counter() - t) * 1000
        _norm(dep, "dependencyScore")
        for d in dep:
            d.setdefault("reason", "dependency expansion")
        fused += dep

    ranked = reranker.rerank(fused, settings.weights, query)
    lat["totalMs"] = (time.perf_counter() - t0) * 1000
    return ranked[:limit * 2], lat


def _fuse(lists: list[list[dict]], k: int) -> list[dict]:
    scores: dict[str, float] = {}
    docs: dict[str, dict] = {}
    for lst in lists:
        for rank, d in enumerate(lst, 1):
            key = _key(d)
            if key not in docs:
                merged = dict(d)
                docs[key] = merged
            else:
                for f in ("lexicalScore", "semanticScore", "symbolScore", "lexMatched", "symMatched"):
                    if d.get(f):
                        docs[key][f] = d[f]
                if len(str(d.get("reason", ""))) > len(str(docs[key].get("reason", ""))):
                    docs[key]["reason"] = f"{docs[key].get('reason','')} + {d.get('reason','')}".strip(" +")
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
    out = []
    for key, s in scores.items():
        d = docs[key]
        d["rrfScore"] = s
        out.append(d)
    return sorted(out, key=lambda d: d["rrfScore"], reverse=True)
