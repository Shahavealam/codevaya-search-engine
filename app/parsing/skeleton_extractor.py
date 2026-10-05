"""Skeleton extraction: structure without implementation bodies."""
from __future__ import annotations

from app.models.file import ClassSkeleton, FileSkeleton


def build_skeleton(path: str, symbols: list[dict], imports: list[str], exports: list[str]) -> FileSkeleton:
    classes: dict[str, ClassSkeleton] = {}
    interfaces: list[str] = []
    types: list[str] = []
    for s in symbols:
        if s["type"] == "class":
            classes.setdefault(s["name"], ClassSkeleton(name=s["name"]))
        elif s["type"] == "method" and s.get("parent") in classes:
            classes[s["parent"]].methods.append(s["signature"])
        elif s["type"] == "interface":
            interfaces.append(s["name"])
        elif s["type"] == "type":
            types.append(s["name"])
    return FileSkeleton(
        path=path, imports=imports, exports=exports,
        classes=list(classes.values()), interfaces=interfaces, types=types,
    )
