"""Dependency search shim (kept as separate module per spec layout)."""
from app.retrieval.symbol_search import dependency_expand as expand  # noqa: F401

__all__ = ["expand"]
