"""RRF + reranker + skeleton + redactor unit tests (no Mongo needed)."""
from app.models.file import FileSkeleton
from app.parsing import import_extractor, skeleton_extractor, symbol_extractor
from app.retrieval import reranker, rrf
from app.security import secret_redactor


def test_rrf_fusion_prefers_consensus():
    a = [{"id": "x", "v": 1}, {"id": "y", "v": 1}]
    b = [{"id": "y", "v": 1}, {"id": "z", "v": 1}]
    fused = rrf.fuse([a, b], k=60)
    assert fused[0]["id"] == "y"


def test_rerank_exact_identifier_boost():
    w = {"lexical": .3, "semantic": .25, "symbol": .2, "dependency": .15, "recency": .1}
    docs = [
        {"path": "a.py", "lexicalScore": .5, "semanticScore": .9, "lexMatched": False},
        {"path": "b.py", "lexicalScore": .5, "semanticScore": .1,
         "symbolScore": .8, "lexMatched": True, "symMatched": True},
    ]
    out = reranker.rerank(docs, w, query="AuthService.refresh")
    assert out[0]["path"] == "b.py"


def test_skeleton_has_no_bodies():
    syms = symbol_extractor.parse_symbols(
        "src/auth/AuthService.ts",
        "export class AuthService { login(email, password) { return 1 } refresh(token) { return 2 } }",
        "typescript")
    imps, exps = import_extractor.extract("a.ts", "import x from './y'", "typescript")
    sk = skeleton_extractor.build_skeleton("src/auth/AuthService.ts", syms, imps, exps)
    assert isinstance(sk, FileSkeleton)
    assert "return 1" not in sk.model_dump_json()


def test_secret_redaction():
    red, found = secret_redactor.redact("api_key = 'sk-live-abc123XYZ456'")
    assert found and "sk-live" not in red
    assert secret_redactor.looks_like_secret_file(".env")
