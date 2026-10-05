# FILE 2 — REPOSITORY SEARCH ENGINE APPLICATION SPECIFICATION

## Role

You are a Principal Search/Information Retrieval Engineer.

Build a production-grade repository intelligence and hybrid code search service for a Cursor-like AI coding platform.

The search service is independent from the Deep Agent orchestration service.

Its job is:
- ingest repository metadata
- index source code
- maintain Tree-sitter skeletons
- maintain symbols/dependencies
- provide lexical search
- provide semantic search
- provide hybrid retrieval
- rank candidates
- return compact context to the Deep Agent
- minimize tokens sent to LLMs

Use MongoDB as the primary persistence and search platform.

MongoDB Atlas Search and MongoDB Vector Search should be used where available. Do not introduce Elasticsearch, PostgreSQL, Qdrant or Pinecone unless there is a clearly documented reason. The default architecture must remain MongoDB-centric.

## Required technology

Backend:
- Python 3.12+
- FastAPI
- Pydantic v2
- Motor/PyMongo async-compatible approach appropriate to the selected driver version
- MongoDB Atlas
- MongoDB Search
- MongoDB Vector Search
- Tree-sitter
- BM25-compatible lexical scoring OR MongoDB Atlas Search lexical retrieval
- OpenAI-compatible embedding provider abstraction
- text-embedding-3-small as the default embedding configuration when OpenAI embeddings are selected
- Redis is optional only for hot-cache acceleration; MongoDB remains the source of truth
- pytest
- mypy
- ruff

The service must work with MongoDB Atlas and have a documented local-development mode.

## Architecture

codevaya-search-engine/
  app/
    main.py
    config.py
    dependencies.py

    api/
      routes/
        repositories.py
        indexing.py
        search.py
        symbols.py
        context.py
        health.py

    db/
      mongodb.py
      collections.py
      indexes.py

    ingestion/
      repository_scanner.py
      file_classifier.py
      ignore_rules.py
      incremental_indexer.py

    parsing/
      tree_sitter_parser.py
      skeleton_extractor.py
      symbol_extractor.py
      import_extractor.py

    indexing/
      chunker.py
      lexical_indexer.py
      embedding_indexer.py
      dependency_indexer.py
      index_version.py

    retrieval/
      lexical_search.py
      vector_search.py
      symbol_search.py
      dependency_search.py
      hybrid_search.py
      rrf.py
      reranker.py
      context_selector.py

    cache/
      context_cache.py
      query_cache.py

    security/
      tenant_guard.py
      secret_redactor.py

    models/
      repository.py
      file.py
      chunk.py
      symbol.py
      dependency.py
      search.py

    services/
      repository_service.py
      indexing_service.py
      retrieval_service.py

  tests/
  scripts/
  Dockerfile
  README.md
  pyproject.toml

## MongoDB data model

Use tenant/repository/workspace isolation.

Collections:

tenants
{
  _id,
  name,
  createdAt
}

repositories
{
  _id,
  tenantId,
  workspaceId,
  name,
  rootHash,
  defaultBranch,
  indexVersion,
  createdAt,
  updatedAt
}

files
{
  _id,
  tenantId,
  repositoryId,
  path,
  language,
  size,
  sha256,
  modifiedAt,
  skeleton,
  imports,
  exports,
  symbols,
  ignored,
  indexVersion,
  updatedAt
}

code_chunks
{
  _id,
  tenantId,
  repositoryId,
  fileId,
  path,
  language,
  symbolName,
  symbolType,
  startLine,
  endLine,
  content,
  skeleton,
  embedding,
  hash,
  indexVersion,
  metadata
}

symbols
{
  _id,
  tenantId,
  repositoryId,
  fileId,
  path,
  name,
  qualifiedName,
  type,
  signature,
  startLine,
  endLine,
  parent,
  exported,
  references,
  metadata
}

dependencies
{
  _id,
  tenantId,
  repositoryId,
  sourceFile,
  targetFile,
  sourceSymbol,
  targetSymbol,
  type,
  metadata
}

search_events
{
  _id,
  tenantId,
  repositoryId,
  query,
  filters,
  resultCount,
  latencyMs,
  cacheHit,
  createdAt
}

## MongoDB indexes

Create appropriate compound indexes beginning with tenantId/repositoryId for isolation and query performance.

Examples:
- repositories: tenantId + workspaceId
- files: tenantId + repositoryId + path
- symbols: tenantId + repositoryId + qualifiedName
- dependencies: tenantId + repositoryId + sourceFile
- code_chunks: tenantId + repositoryId + fileId

Create Atlas Search indexes for lexical retrieval.

Create Vector Search indexes for:
code_chunks.embedding

Use dimensions matching the configured embedding model. Do not hard-code an incorrect dimension; make it configuration-driven and validate at startup.

## Repository ingestion

Input:
- repositoryId
- workspaceId
- files or repository snapshot
- index version

Process:

1. discover files
2. apply .gitignore
3. apply .aiignore
4. exclude binaries/secrets/build directories
5. calculate SHA-256
6. skip unchanged files
7. parse changed files
8. extract skeleton
9. extract symbols
10. extract imports/exports
11. update dependency graph
12. split into semantic chunks
13. generate embeddings only for changed/new chunks
14. upsert MongoDB documents
15. remove stale chunks
16. increment index version

Never re-embed unchanged content.

## Chunking

Do not use naive fixed-size chunks as the primary strategy.

Prefer:
- function/method chunks
- class chunks
- interface/type chunks
- module-level chunks
- configuration blocks
- test blocks

Preserve:
- file path
- symbol
- line range
- parent symbol
- imports
- exports
- language

Keep chunks small enough for efficient retrieval but large enough to preserve implementation meaning.

## Tree-sitter skeleton

For each source file return:

{
  "path": "src/auth/AuthService.ts",
  "imports": ["UserRepository", "TokenService"],
  "exports": ["AuthService"],
  "classes": [
    {
      "name": "AuthService",
      "methods": [
        "login(email, password)",
        "refresh(token)"
      ]
    }
  ],
  "interfaces": [],
  "types": []
}

Do not store implementation bodies inside the skeleton field.

## Search APIs

### POST /v1/search/lexical

Input:
{
  repositoryId,
  query,
  filters,
  limit
}

Use MongoDB Atlas Search lexical capabilities.

### POST /v1/search/semantic

Input:
{
  repositoryId,
  query,
  filters,
  limit
}

Generate query embedding and use MongoDB Vector Search.

### POST /v1/search/hybrid

Input:
{
  repositoryId,
  query,
  filters,
  limit,
  includeSymbols,
  includeDependencies
}

Run:
1. lexical retrieval
2. semantic retrieval
3. symbol retrieval
4. dependency expansion
5. result normalization
6. Reciprocal Rank Fusion
7. optional reranking
8. context selection

## Hybrid ranking

Use RRF as the baseline:

RRF(d) = sum(1 / (k + rank_i(d)))

Then optionally apply domain-specific ranking:

score =
  0.30 * lexicalScore
  + 0.25 * semanticScore
  + 0.20 * symbolScore
  + 0.15 * dependencyScore
  + 0.10 * recencyScore

Make weights configurable.

Do not blindly use semantic search when exact identifiers are present. Code search often benefits strongly from lexical and symbol retrieval.

## Context selection

Typical reduction:

1000 candidate chunks
 -> lexical/semantic retrieval
 -> 100 candidates
 -> RRF
 -> 20 candidates
 -> symbol/dependency filtering
 -> 8 candidates
 -> token budget selection
 -> 3-5 chunks
 -> Deep Agent

Return compact results:

{
  "path": "src/auth/service.ts",
  "symbol": "AuthService.refresh",
  "startLine": 40,
  "endLine": 92,
  "score": 0.91,
  "reason": "symbol + dependency + semantic match",
  "content": "..."
}

Do not return unnecessary repository data.

## Token efficiency

Search service must expose token estimates.

For every context result:
- character count
- approximate token count
- priority score

Context selector must obey:
maxFiles
maxChunks
maxTokens

Selection priority:

priority =
  0.30 relevance
  + 0.20 dependency score
  + 0.20 symbol match
  + 0.15 recency
  + 0.15 user selection

Allow the Deep Agent to request:
- skeleton only
- exact lines
- symbol body
- related symbols
- dependencies
- tests
- configuration

## Cache

Cache:
- query result
- repository index version
- context selection
- embeddings
- file hashes

A cache key must include:
tenantId
repositoryId
indexVersion
normalizedQuery
filters
retrievalMode

Never return cached results across tenants.

## Security

Every query must enforce:
tenantId
repositoryId
workspaceId

Never trust repositoryId supplied by an unauthenticated client.

Redact secrets before embedding/indexing.

Do not index:
.env
private keys
certificates
credentials
cloud credentials
tokens

Support configurable patterns.

## Performance

Requirements:
- incremental indexing
- async background indexing
- concurrent parsing with bounded workers
- embedding batches
- bulk MongoDB writes
- no duplicate embeddings
- projection of only required fields
- pagination
- query timeout
- cache hot queries
- structured latency metrics

Measure:
- lexical latency
- vector latency
- symbol latency
- hybrid latency
- embedding latency
- MongoDB latency
- result count
- token count
- cache hit rate

## API contract for Deep Agent

POST /v1/context/select

Request:
{
  "tenantId": "...",
  "repositoryId": "...",
  "query": "...",
  "activeFile": "...",
  "selectedFiles": [],
  "selectedSymbols": [],
  "maxTokens": 6000,
  "mode": "hybrid"
}

Response:
{
  "repositoryId": "...",
  "indexVersion": "...",
  "files": [],
  "symbols": [],
  "dependencies": [],
  "chunks": [],
  "tokenEstimate": 4800
}

Also provide:
GET /v1/repositories/{repositoryId}/symbols/{qualifiedName}
POST /v1/repositories/{repositoryId}/index
POST /v1/repositories/{repositoryId}/index/file
GET /health

## Evaluation

Create a benchmark dataset containing:
- exact identifier searches
- semantic feature searches
- dependency searches
- bug-fix context searches
- test discovery
- multi-file refactor discovery

Measure:
- Recall@5
- Recall@10
- MRR
- context precision
- token reduction
- latency
- cache hit ratio

Target:
The search engine should reduce a large repository to a small, highly relevant context before any expensive LLM call.

## Deliverable

Generate the complete application.

Do not implement a generic RAG chatbot.

This is a repository intelligence/search engine specifically optimized for software engineering agents.
