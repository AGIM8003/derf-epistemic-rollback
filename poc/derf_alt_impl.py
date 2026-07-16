#!/usr/bin/env python3
"""
DERF Alternative Implementation — Matrix / Warshall transitive closure.

Author: Agim Haxhijaha, ORCID 0009-0002-3234-7765

DISCLAIMER: PoC alternative implementation only. Not production, not peer reviewed.
Uses adjacency-matrix Warshall closure instead of DAG BFS traversal.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUTHOR = "Agim Haxhijaha"
ORCID = "0009-0002-3234-7765"

# Canonical fixture matching derf_poc.py contamination scenario (item IDs)
ITEMS = ["K1", "K2", "K3", "K4", "K5", "K6", "K7"]
# Edges: source -> dependent (row = source, col = dependent for Warshall reachability)
# K1 contaminates K3,K4,K5,K6,K7; K2 is clean calibration used for replay of some items
EDGES = [
    ("K1", "K3"),
    ("K1", "K4"),
    ("K3", "K5"),
    ("K4", "K6"),
    ("K5", "K7"),
    ("K6", "K7"),
    ("K2", "K5"),  # clean alternate for partial replay
]
CONTAMINATED_ORIGIN = "K1"
CLEAN_FRONTIER = {"K2"}
REPLAYABLE = {"K5"}  # can be re-derived from K2 alone after excision


def index_map(ids: list[str]) -> dict[str, int]:
    return {i: n for n, i in enumerate(ids)}


def build_adj(ids: list[str], edges: list[tuple[str, str]]) -> list[list[int]]:
    n = len(ids)
    idx = index_map(ids)
    m = [[0] * n for _ in range(n)]
    for a, b in edges:
        m[idx[a]][idx[b]] = 1
    for i in range(n):
        m[i][i] = 1  # reflexive for closure convenience
    return m


def warshall(m: list[list[int]]) -> list[list[int]]:
    n = len(m)
    r = [row[:] for row in m]
    for k in range(n):
        for i in range(n):
            if r[i][k]:
                for j in range(n):
                    r[i][j] = r[i][j] or r[k][j]
    return r


def causal_closure(ids: list[str], reach: list[list[int]], origin: str) -> list[str]:
    idx = index_map(ids)
    o = idx[origin]
    return sorted(ids[j] for j in range(len(ids)) if reach[o][j] and ids[j] != origin) + [origin]


def barrier_excision(closure: list[str], reach: list[list[int]], ids: list[str]) -> list[str]:
    """Excise in dependency order: sinks first (reverse topo by reachability)."""
    idx = index_map(ids)
    # order by number of remaining descendants in closure
    def descendants(x: str) -> int:
        i = idx[x]
        return sum(1 for y in closure if reach[i][idx[y]] and y != x)

    return sorted(closure, key=descendants)


def clean_replay(excised: list[str], clean: set[str]) -> dict[str, str]:
    results: dict[str, str] = {}
    for item in excised:
        if item in REPLAYABLE and CLEAN_FRONTIER & clean:
            results[item] = "REPLAYED_FROM_CLEAN"
        elif item in clean:
            results[item] = "CLEAN_RETAINED"
        else:
            results[item] = "UNRECOVERABLE"
    return results


def recontamination_rejected(reach: list[list[int]], ids: list[str], origin: str, probe: str) -> bool:
    idx = index_map(ids)
    # reject if probe is reachable from retracted origin (or is the origin)
    return bool(reach[idx[origin]][idx[probe]])


def run_alt() -> dict[str, Any]:
    adj = build_adj(ITEMS, EDGES)
    reach = warshall(adj)
    closure = causal_closure(ITEMS, reach, CONTAMINATED_ORIGIN)
    excision_order = barrier_excision(closure, reach, ITEMS)
    replay = clean_replay(excision_order, CLEAN_FRONTIER)
    probes = ["K4", "K7", "K2"]
    rejections = {p: recontamination_rejected(reach, ITEMS, CONTAMINATED_ORIGIN, p) for p in probes}
    return {
        "implementation": "matrix_warshall",
        "contaminated_origin": CONTAMINATED_ORIGIN,
        "causal_closure": sorted(set(closure)),
        "excision_order": excision_order,
        "excision_set": sorted(set(excision_order)),
        "replay": replay,
        "recontamination_rejection": rejections,
        "recontamination_blocked": all(rejections[p] for p in ["K4", "K7"]),
    }


def run_reference_dag() -> dict[str, Any]:
    """Reference DAG closure for same fixture (independent of derf_poc imports)."""
    children: dict[str, list[str]] = {i: [] for i in ITEMS}
    for a, b in EDGES:
        children[a].append(b)
    # BFS descendants of K1 including K1
    seen: set[str] = set()
    stack = [CONTAMINATED_ORIGIN]
    while stack:
        x = stack.pop()
        if x in seen:
            continue
        seen.add(x)
        stack.extend(children[x])
    closure = sorted(seen)
    # topo excision: sinks first
    def depth(x: str) -> int:
        # longest path from origin
        if x == CONTAMINATED_ORIGIN:
            return 0
        best = 0
        for a, b in EDGES:
            if b == x and a in seen:
                best = max(best, depth(a) + 1)
        return best

    excision = sorted(closure, key=lambda x: -depth(x))
    replay = clean_replay(excision, CLEAN_FRONTIER)
    # reachability for recontam
    adj = build_adj(ITEMS, EDGES)
    reach = warshall(adj)
    probes = ["K4", "K7", "K2"]
    rejections = {p: recontamination_rejected(reach, ITEMS, CONTAMINATED_ORIGIN, p) for p in probes}
    return {
        "implementation": "dag_bfs_reference",
        "contaminated_origin": CONTAMINATED_ORIGIN,
        "causal_closure": closure,
        "excision_order": excision,
        "excision_set": sorted(set(excision)),
        "replay": replay,
        "recontamination_rejection": rejections,
        "recontamination_blocked": all(rejections[p] for p in ["K4", "K7"]),
    }


def compare(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    same_set = set(a["excision_set"]) == set(b["excision_set"])
    same_replay_keys = set(a["replay"]) == set(b["replay"])
    same_replay_status = all(a["replay"].get(k) == b["replay"].get(k) for k in a["replay"])
    same_block = a["recontamination_blocked"] == b["recontamination_blocked"]
    agree = same_set and same_replay_status and same_block
    return {
        "same_excision_set": same_set,
        "same_replay": same_replay_keys and same_replay_status,
        "same_recontamination_block": same_block,
        "implementations_agree": agree,
    }


def main() -> int:
    print("DERF Alternative Implementation (Warshall matrix)")
    print(f"Author: {AUTHOR} ORCID {ORCID}")
    alt = run_alt()
    ref = run_reference_dag()
    cmp = compare(alt, ref)
    evidence = {
        "framework": "DERF",
        "author": AUTHOR,
        "orcid": ORCID,
        "disclaimer": "PoC replication evidence only — not production",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "primary_style": "dag_bfs",
        "alternative_style": "matrix_warshall",
        "alt": alt,
        "reference": ref,
        "comparison": cmp,
        "replication_pass": cmp["implementations_agree"],
    }
    out = Path(__file__).resolve().parent / "derf_replication_evidence.json"
    out.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"Excision set (alt): {alt['excision_set']}")
    print(f"Excision set (ref): {ref['excision_set']}")
    print(f"Replication agree: {cmp['implementations_agree']}")
    print(f"Evidence: {out}")
    return 0 if cmp["implementations_agree"] else 1


if __name__ == "__main__":
    sys.exit(main())
