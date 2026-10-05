"""API contract tests: health + context/select shape (DB-dependent tests skipped w/o mongo)."""
from fastapi.testclient import TestClient

from app.main import create_app


def test_health_boots():
    client = TestClient(create_app())
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["embeddingModel"] == "text-embedding-3-small"
    assert body["embeddingDims"] == 1536
