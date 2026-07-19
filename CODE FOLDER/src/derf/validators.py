"""DERF input validation."""
from __future__ import annotations

from typing import Iterable


def validate_item_id(item_id: str) -> str:
    if not isinstance(item_id, str) or not item_id.strip():
        raise ValueError("item_id must be a non-empty string")
    return item_id.strip()


def validate_sources(sources: Iterable[str] | None) -> list[str]:
    if sources is None:
        return []
    out = list(sources)
    for s in out:
        if not isinstance(s, str) or not s.strip():
            raise ValueError("all source/dependency ids must be non-empty strings")
    return out


def detect_cycles(items: dict[str, list[str]]) -> None:
    """Raise ValueError if dependency edges contain a cycle."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {k: WHITE for k in items}

    def visit(node: str) -> None:
        color[node] = GRAY
        for nxt in items.get(node, []):
            if nxt not in color:
                continue
            if color[nxt] == GRAY:
                raise ValueError(f"circular dependency involving '{node}' -> '{nxt}'")
            if color[nxt] == WHITE:
                visit(nxt)
        color[node] = BLACK

    for node in list(items):
        if color[node] == WHITE:
            visit(node)
