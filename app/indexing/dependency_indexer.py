"""Dependency graph indexer: resolve imports to workspace files."""
from __future__ import annotations


def _resolve_import(imp: str, files: set[str], source: str) -> str | None:
    imp = imp.strip()
    if imp.startswith("."):
        # Relative: src/a.ts importing ./b -> src/b (+extensions / index)
        base = source.rsplit("/", 1)[0] if "/" in source else ""
        target = (base + "/" + imp.lstrip("./")).replace("//", "/")
        for cand in (target, target + ".py", target + ".ts", target + ".js",
                     target + "/__init__.py", target + "/index.ts"):
            if cand in files:
                return cand
        return None
    # Absolute-ish: match suffix (myapp.users.repo -> users/repo.py)
    norm = imp.replace(".", "/")
    for f in files:
        if f.endswith(norm + ".py") or f.endswith(norm + ".ts") or f.endswith(norm + ".js") or f == norm:
            return f
    return None


def build_edges(
    tenant_id: str, repo_id: str, file_imports: dict[str, list[str]], all_files: set[str],
) -> list[dict]:
    edges = []
    for src, imports in file_imports.items():
        for imp in imports:
            tgt = _resolve_import(imp, all_files, src)
            if tgt:
                edges.append({
                    "tenantId": tenant_id, "repositoryId": repo_id,
                    "sourceFile": src, "targetFile": tgt,
                    "sourceSymbol": "", "targetSymbol": "",
                    "type": "import", "metadata": {"raw": imp},
                })
    return edges
