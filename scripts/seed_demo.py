"""Seed a tiny demo repo via the API (works with local Mongo or Atlas)."""
import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
TENANT = "demo-tenant"

FILES = [
    {"path": "src/auth/service.py",
     "content": "class AuthService:\n    def login(self, email, password):\n        return sign(email)\n    def refresh(self, token):\n        return renew(token)\n"},
    {"path": "src/auth/repo.py",
     "content": "from .service import AuthService\nclass UserRepository:\n    def find(self, email):\n        return None\n"},
    {"path": "src/main.py",
     "content": "from auth.service import AuthService\nsvc = AuthService()\nprint(svc.login('a@b.c', 'x'))\n"},
]

c = httpx.Client(base_url=BASE, headers={"X-Tenant-ID": TENANT})
repo = c.post("/v1/repositories", json={"tenantId": TENANT, "name": "demo"}).json()
rid = repo["_id"]
print("repo:", rid)
print(c.post(f"/v1/repositories/{rid}/index", json={"files": FILES}).json())
print(c.post("/v1/search/hybrid", json={"repositoryId": rid, "query": "AuthService login"}).json())
