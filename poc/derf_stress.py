#!/usr/bin/env python3
"""
DERF Stress-Scale Test — 1000 knowledge items, 200 agents, 50 contamination sources.

Author: Agim Haxhijaha, ORCID 0009-0002-3234-7765
"""

from __future__ import annotations

import json
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from derf_poc import Agent, EpistemicGraph, KnowledgeItem

AUTHOR = "Agim Haxhijaha"
ORCID = "0009-0002-3234-7765"
OUT = Path(__file__).with_name("derf_stress_results.json")

BASE = {"items": 1000, "agents": 200, "origins": 50}


def build_scale(items: int, agents: int, origins: int) -> tuple[EpistemicGraph, set[str]]:
    g = EpistemicGraph()
    # Create agents
    for a in range(agents):
        deps = []
        if a > 0:
            deps = [f"agent_{a-1:03d}"]
            if a > 10 and a % 7 == 0:
                deps.append(f"agent_{a//2:03d}")
        g.add_agent(Agent(f"agent_{a:03d}", f"role_{a%12}", depends_on=deps))

    # Layered items: first 50 are roots; rest depend on prior items
    for i in range(items):
        agent_id = f"agent_{i % agents:03d}"
        if i < origins:
            sources: list[str] = []
        else:
            # Fan-in from up to 3 earlier items
            sources = [f"K_{i-1:04d}"]
            if i >= 2:
                sources.append(f"K_{i-2:04d}")
            if i >= 10 and i % 3 == 0:
                sources.append(f"K_{i % (i//2):04d}" if i // 2 else "K_0000")
            # Ensure valid ids
            sources = [s for s in sources if int(s.split("_")[1]) < i]
            if not sources:
                sources = [f"K_{i-1:04d}"]
        item = KnowledgeItem(
            f"K_{i:04d}",
            agent_id,
            f"claim_{i}",
            source_ids=sources,
            derived=bool(sources),
        )
        g.items[item.item_id] = item
        g.agents[agent_id].knowledge[item.item_id] = item

    origin_ids = {f"K_{i:04d}" for i in range(origins)}
    return g, origin_ids


def run_once(items: int, agents: int, origins: int) -> dict[str, Any]:
    tracemalloc.start()
    t0 = time.perf_counter()
    g, origins_set = build_scale(items, agents, origins)
    t_build = time.perf_counter() - t0

    for oid in origins_set:
        g.mark_retracted(oid)

    t1 = time.perf_counter()
    closure = g.compute_causal_closure(origins_set)
    t_closure = time.perf_counter() - t1

    t2 = time.perf_counter()
    excision = g.barrier_ordered_excision(closure)
    t_excision = time.perf_counter() - t2

    t3 = time.perf_counter()
    replay = g.replay_from_frontier()
    t_replay = time.perf_counter() - t3

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    total = time.perf_counter() - t0

    return {
        "scale": {"items": items, "agents": agents, "origins": origins},
        "timing_s": {
            "build": round(t_build, 6),
            "closure": round(t_closure, 6),
            "excision": round(t_excision, 6),
            "replay": round(t_replay, 6),
            "total": round(total, 6),
            "per_closure_item_ms": round(1000 * t_closure / max(len(closure), 1), 6),
        },
        "memory": {
            "current_bytes": current,
            "peak_bytes": peak,
            "peak_mb": round(peak / (1024 * 1024), 4),
        },
        "results": {
            "closure_size": len(closure),
            "excision_count": len(excision),
            "frontier_size": replay["frontier_size"],
            "replayed": len(replay["replayed"]),
            "unrecoverable": len(replay["unrecoverable"]),
        },
    }


def main() -> int:
    multipliers = [1, 2, 5, 10]
    curve = []
    for m in multipliers:
        items = BASE["items"] * m
        agents = BASE["agents"] * m
        origins = BASE["origins"] * m
        print(f"DERF stress {m}x items={items} agents={agents} origins={origins} ...")
        row = run_once(items, agents, origins)
        row["multiplier"] = m
        curve.append(row)
        print(f"  total={row['timing_s']['total']}s peak_mb={row['memory']['peak_mb']}")

    # Bottleneck = slowest op at 1x and growth of ops
    base_t = curve[0]["timing_s"]
    ops = ["build", "closure", "excision", "replay"]
    bottleneck = max(ops, key=lambda k: base_t[k])
    growth = {
        op: [
            {
                "multiplier": r["multiplier"],
                "seconds": r["timing_s"][op],
                "vs_1x": round(r["timing_s"][op] / max(base_t[op], 1e-9), 3),
            }
            for r in curve
        ]
        for op in ops
    }

    out = {
        "framework": "DERF",
        "script": "derf_stress.py",
        "author": AUTHOR,
        "orcid": ORCID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_target": BASE,
        "scalability_curve": curve,
        "bottleneck_operation": bottleneck,
        "bottleneck_rationale": (
            f"At 1× base scale, '{bottleneck}' dominates wall time among measured ops; "
            "growth curve shows which op degrades fastest under scale-up."
        ),
        "growth_by_operation": growth,
        "pass": all(r["results"]["closure_size"] > 0 for r in curve) and len(curve) == 4,
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"bottleneck={bottleneck} pass={out['pass']}")
    print(f"Wrote {OUT.name}")
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
