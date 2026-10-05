"""End-to-end hybrid test with in-memory fake DB (no Mongo/Atlas needed)."""
import pytest

from app.config import Settings
from app.indexing.embedding_indexer import HashEmbeddingProvider
from app.retrieval import hybrid_search

AUTH = '''class AuthService:
    def login(self, email, password):
        """Authenticate user and return token."""
        return sign(email)

    def refresh(self, token):
        return renew(token)
'''
OTHER = '''def unrelated_helper():
    return 42
'''


class FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    def limit(self, n):
        return FakeCursor(self._docs[:n])

    async def to_list(self, length=100):
        return self._docs[:length]


class FakeCollection:
    def __init__(self, docs):
        self._docs = docs

    def find(self, q=None, proj=None):
        docs = list(self._docs)
        if q:
            lang = q.get("language")
            if lang:
                docs = [d for d in docs if d.get("language") == lang]
            pre = (q.get("path") or {}).get("$regex", "")
            if pre:
                docs = [d for d in docs if d.get("path", "").startswith(pre.lstrip("^"))]
        return FakeCursor(docs)

    def aggregate(self, pipe):
        raise RuntimeError("no atlas in test")  # forces local fallbacks

    async def find_one(self, q=None, proj=None):
        for d in self._docs:
            ok = True
            for k, v in (q or {}).items():
                if k == "$or":
                    if not any(d.get(sk) == sv for c in v for sk, sv in c.items()):
                        ok = False
                elif isinstance(v, dict) and "$in" in v:
                    if d.get(k) not in v["$in"]:
                        ok = False
                elif d.get(k) != v:
                    ok = False
            if ok:
                return dict(d)
        return None


class FakeDB(dict):
    pass


def _chunk(path, sym, content, vec):
    return {"path": path, "symbolName": sym, "startLine": 1, "endLine": 5,
            "content": content, "language": "python", "embedding": vec,
            "tenantId": "t1", "repositoryId": "r1"}


@pytest.mark.asyncio
async def test_hybrid_finds_auth_service():
    s = Settings(embedding_provider="hash", embedding_dims=64)
    prov = HashEmbeddingProvider(64)
    va = (await prov.embed([AUTH]))[0]
    vo = (await prov.embed([OTHER]))[0]
    db = FakeDB({
        "code_chunks": FakeCollection([
            _chunk("src/auth.py", "AuthService.login", AUTH, va),
            _chunk("src/util.py", "unrelated_helper", OTHER, vo),
        ]),
        "symbols": FakeCollection([
            {"path": "src/auth.py", "name": "login", "qualifiedName": "AuthService.login"},
        ]),
        "dependencies": FakeCollection([]),
    })
    ranked, lat = await hybrid_search.hybrid(
        db, s, prov, "t1", "r1", "AuthService login", limit=5)
    assert ranked and ranked[0]["path"] == "src/auth.py"
    assert "totalMs" in lat
