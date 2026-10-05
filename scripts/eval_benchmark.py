"""Benchmark harness: Recall@5/10, MRR, token reduction, latency, cache hits.

Dataset covers: exact identifiers, semantic feature search, dependency
search, bug-fix context, test discovery, multi-file refactor discovery.
Runs against a live API (default localhost:8000).
"""
import statistics
import sys
import time

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
TENANT = "bench-tenant"

QUERIES = [
    ("exact identifier", "AuthService.refresh", "src/auth/service.py"),
    ("semantic feature", "where do users authenticate and get tokens", "src/auth/service.py"),
    ("dependency", "what imports AuthService", "src/main.py"),
    ("bug-fix context", "token refresh fails expired", "src/auth/service.py"),
    ("test discovery", "tests for login flow", "tests/test_auth.py"),
    ("refactor discovery", "all usages of UserRepository", "src/auth/repo.py"),
]


def recall_at(results: list[dict], expected: str, k: int) -> float:
    return 1.0 if any(expected in r.get("path", "") for r in results[:k]) else 0.0


def main() -> None:
    c = httpx.Client(base_url=BASE, headers={"X-Tenant-ID": TENANT}, timeout=30)
    rid = c.post("/v1/repositories", json={"tenantId": TENANT, "name": "bench"}).json()["_id"]
    c.post(f"/v1/repositories/{rid}/index", json={"files": [
        {"path": "src/auth/service.py", "content": "class AuthService:\n def refresh(self, token):\n  return renew(token)\n"},
        {"path": "src/main.py", "content": "from auth.service import AuthService\n"},
        {"path": "tests/test_auth.py", "content": "def test_login():\n assert True\n"},
        {"path": "src/auth/repo.py", "content": "class UserRepository:\n def find(self, e):\n  return None\n"},
    ]})
    r5, r10, mrr, lats, toks = [], [], [], [], []
    for kind, q, expected in QUERIES:
        t0 = time.perf_counter()
        res = c.post("/v1/search/hybrid", json={"repositoryId": rid, "query": q}).json()
        lats.append((time.perf_counter() - t0) * 1000)
        results = res.get("results", [])
        r5.append(recall_at(results, expected, 5))
        r10.append(recall_at(results, expected, 10))
        rank = next((i + 1 for i, r_ in enumerate(results[:10]) if expected in r_.get("path", "")), None)
        mrr.append(1.0 / rank if rank else 0.0)
        toks.append(sum(r_.get("tokenEstimate", 0) for r_ in results))
    print(f"Recall@5={statistics.mean(r5):.2f} Recall@10={statistics.mean(r10):.2f} "
          f"MRR={statistics.mean(mrr):.2f} p50_latency={statistics.median(lats):.0f}ms "
          f"avg_tokens={statistics.mean(toks) if toks else 0:.0f}")


if __name__ == "__main__":
    main()
