"""Import / export extraction (dependency graph input)."""
from __future__ import annotations

import re

PY_IMPORT = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w., ]+))", re.MULTILINE)
JS_IMPORT = re.compile(r"""^\s*import\s+(?:[\w*{}, ]+\s+from\s+)?['"]([^'"]+)['"]""", re.MULTILINE)
JS_REQUIRE = re.compile(r"""require\(\s*['"]([^'"]+)['"]\s*\)""")
PY_EXPORT = re.compile(r"^__all__\s*=\s*\[(.*?)\]", re.MULTILINE | re.DOTALL)
JS_EXPORT = re.compile(r"^\s*export\s+(?:default\s+)?(?:class|function|const|let|var|interface|type)?\s*(\w+)?", re.MULTILINE)


def extract(path: str, content: str, language: str) -> tuple[list[str], list[str]]:
    imports: list[str] = []
    exports: list[str] = []
    if language == "python":
        for im in PY_IMPORT.finditer(content):
            imports.append(im.group(1) or im.group(2).split(",")[0].strip())
        m = PY_EXPORT.search(content)
        if m:
            exports += re.findall(r"""['"](\w+)['"]""", m.group(1))
    elif language in {"javascript", "typescript"}:
        imports += JS_IMPORT.findall(content) + JS_REQUIRE.findall(content)
        exports += [e for e in JS_EXPORT.findall(content) if e]
    # Resolve relative imports to file-ish targets later in dependency_indexer.
    return sorted(set(imports)), sorted(set(exports))
