"""Secret redaction before embedding/indexing. Never index credentials."""
from __future__ import annotations

import os
import re

DEFAULT_PATTERNS = [
    r"(?i)(api[_-]?key\s*[:=]\s*)(['\"]?)[\w\-./+]{8,}\2",
    r"(?i)(secret\s*[:=]\s*)(['\"]?)[\w\-./+]{8,}\2",
    r"(?i)(password\s*[:=]\s*)(['\"]?)[^\s'\"]{4,}\2",
    r"(?i)(bearer\s+)[A-Za-z0-9\-._~+/]+",
    r"xox[baprs]-[A-Za-z0-9\-]+",
    r"sk-(live|test)-[A-Za-z0-9]+",
    r"AKIA[0-9A-Z]{16}",
    r"-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----",
    r"gh[pousr]_[A-Za-z0-9]+",
]

_COMPILED = [re.compile(p) for p in DEFAULT_PATTERNS]
REDACTED = "[REDACTED]"


def extra_patterns() -> list[re.Pattern]:
    raw = os.getenv("SECRET_REDACT_PATTERNS", "")
    return [re.compile(p) for p in raw.split(";;") if p.strip()]


def redact(text: str) -> tuple[str, bool]:
    """Return (redacted_text, found_secret)."""
    found = False
    for rx in _COMPILED + extra_patterns():
        if rx.search(text):
            found = True
            text = rx.sub(REDACTED, text)
    return text, found


def looks_like_secret_file(path: str) -> bool:
    low = path.lower()
    return any(k in low for k in (".env", ".pem", ".key", "credentials", "secrets", "id_rsa", ".p12", ".pfx"))
