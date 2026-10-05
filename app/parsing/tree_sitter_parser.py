"""Optional tree-sitter grammar backend.

If `tree_sitter_python` / `tree_sitter_javascript` / `tree_sitter_typescript`
/ `tree_sitter_go` are installed, they are used; otherwise HAS_GRAMMARS is
False and callers fall back to regex parsing. No hard dependency.
"""
from __future__ import annotations

HAS_GRAMMARS = False

try:  # pragma: no cover - exercised only when grammars installed
    import tree_sitter_python  # type: ignore
    HAS_GRAMMARS = True
except Exception:
    tree_sitter_python = None  # type: ignore


def parse_with_grammars(path: str, content: str, language: str) -> list[dict]:
    """Best-effort tree-sitter parse. Returns [] when grammar unavailable."""
    if not HAS_GRAMMARS:
        return []
    try:
        import tree_sitter
        lang_map = {}
        if tree_sitter_python is not None:
            lang_map["python"] = tree_sitter.Language(tree_sitter_python.language())
        if language not in lang_map:
            return []
        parser = tree_sitter.Parser(lang_map[language])
        tree = parser.parse(content.encode())
        out: list[dict] = []

        def walk(node, parent=""):
            kind_map = {
                "class_definition": "class",
                "function_definition": "function",
            }
            t = kind_map.get(node.type)
            if t:
                name_node = node.child_by_field_name("name")
                name = content[node.start_byte:node.end_byte].split("(")[0].strip() if False else (
                    content[name_node.start_byte:name_node.end_byte] if name_node else "?"
                )
                if t == "function" and parent:
                    t = "method"
                out.append({
                    "name": name,
                    "qualifiedName": f"{parent}.{name}" if parent else name,
                    "type": t,
                    "signature": name,
                    "startLine": node.start_point[0] + 1,
                    "endLine": node.end_point[0] + 1,
                    "parent": parent, "exported": False,
                })
                parent = f"{parent}.{name}" if parent else name
            for ch in node.children:
                walk(ch, parent)

        walk(tree.root_node)
        return out
    except Exception:
        return []
