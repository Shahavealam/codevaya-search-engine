"""Tree-sitter parsing with a dependency-free regex fallback.

Tries `tree_sitter` grammars when installed; otherwise (and in tests) uses
careful regex parsing for Python/JS/TS/Go/Java. Public output is a uniform
list of symbol dicts so downstream code never branches on the backend.
"""
from __future__ import annotations

import re


def _regex_symbols(path: str, content: str, language: str) -> list[dict]:
    lines = content.splitlines()
    syms: list[dict] = []

    def add(name, typ, start, end, parent="", signature="", exported=False):
        syms.append({
            "name": name, "qualifiedName": f"{parent}.{name}" if parent else name,
            "type": typ, "signature": signature or name,
            "startLine": start, "endLine": end, "parent": parent,
            "exported": exported,
        })

    if language == "python":
        stack: list[tuple[str, int]] = []  # (name, indent)
        for i, line in enumerate(lines, 1):
            m = re.match(r"^(\s*)(class|def)\s+([A-Za-z_]\w*)\s*(\(.*\))?:?", line)
            if not m:
                continue
            indent, kind, name, sig = m.group(1), m.group(2), m.group(3), m.group(4) or ""
            level = len(indent.expandtabs(4))
            while stack and stack[-1][1] >= level:
                stack.pop()
            parent = stack[-1][0] if stack else ""
            typ = "class" if kind == "class" else ("method" if parent else "function")
            # end line: next symbol at same/lower indent or EOF
            end = len(lines)
            for j in range(i, len(lines)):
                m2 = re.match(r"^(\s*)(class|def)\s+\w+", lines[j])
                if m2 and len(m2.group(1).expandtabs(4)) <= level:
                    end = j
                    break
            add(name, typ, i, end, parent, f"{name}{sig}")
            if kind == "class":
                stack.append((name, level))
        return syms

    # C-like languages: class/interface/function/method + arrow functions
    cls_re = re.compile(r"^\s*(?:export\s+)?(?:abstract\s+)?(class|interface|type)\s+([A-Za-z_]\w*)")
    fn_re = re.compile(
        r"^\s*(?:export\s+)?(?:async\s+)?(?:function\s+([A-Za-z_]\w*)|"
        r"(?:public|private|protected)?\s*([A-Za-z_]\w*)\s*\([^;{]*\)\s*(?::\s*[\w<>\[\]]+\s*)?\{|"
        r"(?:const|let|var)\s+([A-Za-z_]\w*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)"
    )
    current_class = ""
    brace_depth = 0
    for i, line in enumerate(lines, 1):
        mc = cls_re.match(line)
        if mc:
            current_class = mc.group(2)
            add(current_class, mc.group(1).lower(), i, min(i + 60, len(lines)),
                exported="export" in line)
            brace_depth = line.count("{") - line.count("}")
            continue
        mf = fn_re.match(line)
        if mf:
            name = mf.group(1) or mf.group(2) or mf.group(3) or ""
            if name and name not in {"if", "for", "while", "switch", "catch"}:
                typ = "method" if current_class else "function"
                add(name, typ, i, min(i + 40, len(lines)), current_class,
                    line.strip()[:160], exported="export" in line)
        brace_depth += line.count("{") - line.count("}")
        if brace_depth <= 0:
            current_class = ""
    return syms


def parse_symbols(path: str, content: str, language: str) -> list[dict]:
    """Return uniform symbol dicts, preferring tree-sitter when grammars exist."""
    try:
        import tree_sitter  # noqa: F401

        # Grammar packages (tree_sitter_python etc.) are optional; if none are
        # installed we silently use the regex backend. This keeps local dev and
        # CI working without native builds while remaining tree-sitter-ready.
        from app.parsing.tree_sitter_parser import HAS_GRAMMARS
        if HAS_GRAMMARS:
            from app.parsing.tree_sitter_parser import parse_with_grammars
            got = parse_with_grammars(path, content, language)
            if got:
                return got
    except Exception:
        pass
    return _regex_symbols(path, content, language)
