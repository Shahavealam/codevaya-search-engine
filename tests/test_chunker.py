"""Chunker tests: semantic (symbol-aware), never naive fixed-size as primary."""
from app.indexing.chunker import chunk_file

PY = '''"""Auth module."""
import os

class AuthService:
    def login(self, email, password):
        return True

    def refresh(self, token):
        return token

def helper():
    return 1
'''


def test_function_and_class_chunks():
    from app.parsing.symbol_extractor import parse_symbols
    syms = parse_symbols("src/auth.py", PY, "python")
    names = {s["qualifiedName"] for s in syms}
    assert "AuthService" in names and "AuthService.login" in names
    chunks = chunk_file("src/auth.py", PY, "python", "code", syms)
    by_sym = {c["symbolName"] for c in chunks}
    assert "AuthService.login" in by_sym
    # implementation preserved in chunk
    login = next(c for c in chunks if c["symbolName"] == "AuthService.login")
    assert "return True" in login["content"]


def test_config_blocks_without_symbols():
    chunks = chunk_file("config.json", '{"a": 1}', "json", "config", [])
    assert chunks and chunks[0]["symbolType"] == "block"
