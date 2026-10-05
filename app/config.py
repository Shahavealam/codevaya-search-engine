"""Central application configuration (Pydantic Settings)."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "codeveya-search-engine"
    env: str = "local"
    api_prefix: str = "/v1"
    log_level: str = "INFO"

    # MongoDB
    mongodb_uri: str = Field(default="mongodb://localhost:27017")
    mongodb_db: str = "codeveya_search"

    # Atlas Search / Vector Search
    atlas_search_index: str = "code_chunks_lexical"
    atlas_vector_index: str = "code_chunks_vector"
    atlas_vector_field: str = "embedding"
    atlas_search_field: str = "content"

    # Embeddings
    embedding_provider: str = "openai"  # openai | hash
    embedding_model: str = "text-embedding-3-small"
    embedding_dims: int = 1536
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    embedding_batch_size: int = 32

    # Retrieval
    rrf_k: int = 60
    w_lexical: float = 0.30
    w_semantic: float = 0.25
    w_symbol: float = 0.20
    w_dependency: float = 0.15
    w_recency: float = 0.10

    # Context budgets
    max_files_default: int = 10
    max_chunks_default: int = 8
    max_tokens_default: int = 6000
    query_timeout_ms: int = 5000

    # Indexing
    index_workers: int = 4

    # Cache
    redis_url: str = ""
    cache_ttl_seconds: int = 300

    @field_validator("embedding_dims")
    @classmethod
    def _validate_dims(cls, v: int) -> int:
        # text-embedding-3-small is 1536 dims; guard against misconfiguration.
        if v <= 0 or v > 8192:
            raise ValueError("embedding_dims must be in (0, 8192]")
        return v

    @property
    def weights(self) -> dict[str, float]:
        return {
            "lexical": self.w_lexical,
            "semantic": self.w_semantic,
            "symbol": self.w_symbol,
            "dependency": self.w_dependency,
            "recency": self.w_recency,
        }

    def validate_vector_dims(self, n: int) -> None:
        if n != self.embedding_dims:
            raise ValueError(
                f"Embedding dim mismatch: got {n}, expected {self.embedding_dims} "
                f"for model {self.embedding_model}"
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
