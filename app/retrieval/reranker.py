"""Weighted reranker: 0.30 lex + 0.25 sem + 0.20 sym + 0.15 dep + 0.10 recency.

Exact identifiers (CamelCase / snake_case / dotted) boost lexical+symbol,
so semantic search never drowns exact matches — per spec.
"""
from __future__ import annotations

import re

IDENT_RE = re.compile(r"[A-Za-z_]\w*(?:[A-Z]\w*|\.\w+|_\w+)")


def has_exact_identifier(query: str) -> bool:
    toks = re.findall(r"[A-Za-z_][\w.]*", query)
    return any(len(t) > 3 and ("." in t or "_" in t or re.search(r"[A-Z]", t[1:])) for t in toks)


def rerank(docs: list[dict], weights: dict[str, float], query: str = "") -> list[dict]:
    boost = 1.25 if has_exact_identifier(query) else 1.0
    out = []
    for d in docs:
        lex = float(d.get("lexicalScore", 0.0)) * (boost if d.get("lexMatched") else 1.0)
        sem = float(d.get("semanticScore", 0.0))
        sym = float(d.get("symbolScore", 0.0)) * (boost if d.get("symMatched") else 1.0)
        dep = float(d.get("dependencyScore", 0.0))
        rec = float(d.get("recencyScore", 0.0))
        score = (
            weights.get("lexical", .30) * lex + weights.get("semantic", .25) * sem
            + weights.get("symbol", .20) * sym + weights.get("dependency", .15) * dep
            + weights.get("recency", .10) * rec
        )
        d = dict(d)
        d["score"] = round(score, 4)
        out.append(d)
    return sorted(out, key=lambda d: d["score"], reverse=True)
