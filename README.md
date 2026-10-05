# CodeVeya Search Engine

Repository intelligence + hybrid code search for a Cursor-like AI coding platform.
MongoDB-centric: Atlas Search (lexical) + Vector Search (semantic) + RRF hybrid
ranking, with Tree-sitter skeletons, symbol/dependency graphs, and token-budgeted
context selection for the Deep Agent.

## Quickstart (local dev, no Atlas/OpenAI needed)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # defaults run fully local (hash embeddings, regex fallback)
uvicorn app.main:app --reload
curl localhost:8000/health
```

Local-dev mode: `EMBEDDING_PROVIDER=openai` with **no** `OPENAI_API_KEY` falls
back to deterministic hash embeddings (correct dims); lexical/vector retrieval
falls back to in-Python scoring when Atlas indexes are unreachable. MongoDB is
still required — use local `mongod` or Docker:

```bash
docker run -d -p 27017:27017 mongo:7
```

## Production (Atlas)

1. Set `MONGODB_URI` to Atlas, `OPENAI_API_KEY` for real embeddings
   (`EMBEDDING_MODEL=text-embedding-3-small`, `EMBEDDING_DIMS=1536`).
2. Emit index definitions and create them in Atlas:
   `python scripts/create_atlas_indexes.py`
3. Startup validates embedding dims and creates compound indexes
   (`tenantId + repositoryId + …`).

## API

| Method | Path | Purpose |
|---|---|---|
| POST | /v1/repositories | create repo |
| GET | /v1/repositories | list (tenant-scoped) |
| POST | /v1/repositories/{id}/index | index snapshot / directory |
| POST | /v1/repositories/{id}/index/file | index one file |
| POST | /v1/search/lexical | Atlas Search lexical |
| POST | /v1/search/semantic | Vector Search |
| POST | /v1/search/hybrid | lexical+semantic+symbol+deps → RRF → rerank |
| POST | /v1/context/select | Deep Agent contract (token-budgeted) |
| GET | /v1/repositories/{id}/symbols[/{qualifiedName}] | symbol lookup |
| GET | /health | probes + dims check |

Auth: `X-Tenant-ID` header (workspace optional). Cache keys include
tenant+repo+indexVersion+query+filters+mode — never shared across tenants.
Secrets (`.env`, keys, tokens) are redacted pre-index and never embedded.

## Pipeline

`1000 chunks → retrieval → 100 → RRF → 20 → symbol/dep filter → 8 → token
budget → 3–5 chunks → Deep Agent`. Weights (`W_LEXICAL…`) and budgets
(`MAX_*`) are env-configurable.

## Checks

```bash
pytest
ruff check app tests
mypy app
python scripts/eval_benchmark.py  # needs live API
```
