"""Embedding provider abstraction (OpenAI-compatible) + batch indexer.

Default model: text-embedding-3-small (1536 dims) when OpenAI is selected.
Local-dev / CI: provider `hash` or automatic fallback when no API key is set —
deterministic, key-free, dimension-correct vectors so the whole pipeline runs
without Atlas or OpenAI.
"""
from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    dims: int

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashEmbeddingProvider(EmbeddingProvider):
    """Deterministic char-trigram hashing encoder (local dev / tests)."""

    def __init__(self, dims: int = 1536):
        self.dims = dims

    async def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            v = [0.0] * self.dims
            low = t.lower()
            for i in range(len(low) - 2):
                tri = low[i:i + 3]
                h = int(hashlib.md5(tri.encode()).hexdigest(), 16)
                v[h % self.dims] += 1.0
            norm = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / norm for x in v])
        return out


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, base_url: str, model: str, dims: int):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dims = dims

    async def embed(self, texts: list[str]) -> list[list[float]]:
        import httpx
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"model": self.model, "input": texts}
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(f"{self.base_url}/embeddings", json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()["data"]
        vecs = [d["embedding"] for d in sorted(data, key=lambda d: d["index"])]
        if vecs and len(vecs[0]) != self.dims:
            raise ValueError(
                f"Embedding dim mismatch: got {len(vecs[0])}, expected {self.dims}"
            )
        return vecs


def build_provider(provider: str, api_key: str, base_url: str, model: str, dims: int) -> EmbeddingProvider:
    if provider == "hash" or not api_key:
        # No key -> deterministic local fallback (documented local-dev mode).
        return HashEmbeddingProvider(dims)
    return OpenAIEmbeddingProvider(api_key, base_url, model, dims)


async def embed_new_chunks(
    provider: EmbeddingProvider, chunks: list[dict], existing_hashes: set[str],
    batch_size: int = 32,
) -> list[dict]:
    """Attach embeddings only to new/changed chunks (never re-embed unchanged)."""
    todo = [c for c in chunks if c["hash"] not in existing_hashes]
    texts = [c["content"] for c in todo]
    for i in range(0, len(texts), batch_size):
        vecs = await provider.embed(texts[i:i + batch_size])
        for c, v in zip(todo[i:i + batch_size], vecs):
            c["embedding"] = v
    return chunks
