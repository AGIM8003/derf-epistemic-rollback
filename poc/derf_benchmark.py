#!/usr/bin/env python3
"""
DERF Benchmark Harness — Epistemic Rollback Performance & Correctness

Author: Agim Haxhijaha, ORCID 0009-0002-3234-7765

DISCLAIMER: Proof-of-concept benchmark only. Not production validation.
Stdlib only. Reuses derf_gate.py logic.
"""

from __future__ import annotations

import json
import sys
import time
import tracemalloc
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from derf_gate import (
    ATTACK_STRATEGIES,
    Agent,
    EpistemicGraph,
    KnowledgeItem,
    build_concurrent_contamination_graph,
    build_minimal_scenario,
    build_partial_observability_graph,
    build_performance_graph,
    build_scale_graph,
    run_adversarial_battery,
)

AUTHOR = "Agim Haxhijaha"
ORCID = "0009-0002-3234-7765"
DISCLAIMER = "PoC benchmark only — not production, not peer reviewed"
RESULTS_FILE = "derf_benchmark_results.json"


@dataclass
class ScenarioResult:
    name: str
    size: str
    expected_pass: bool
    actual_pass: bool
    execution_time_ms: float
    memory_bytes_peak: int
    details: dict[str, Any]


def _measure(run: Callable[[], tuple[bool, dict[str, Any]]]) -> ScenarioResult:
    tracemalloc.start()
    t0 = time.perf_counter()
    actual_pass, details = run()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return ScenarioResult(
        name=details.pop("_name"),
        size=details.pop("_size"),
        expected_pass=details.pop("_expected_pass"),
        actual_pass=actual_pass,
        execution_time_ms=round(elapsed_ms, 3),
        memory_bytes_peak=peak,
        details=details,
    )


def _wrap(
    name: str, size: str, expected_pass: bool, fn: Callable[[], tuple[bool, dict[str, Any]]]
) -> Callable[[], ScenarioResult]:
    def runner() -> ScenarioResult:
        def inner() -> tuple[bool, dict[str, Any]]:
            ok, details = fn()
            details["_name"] = name
            details["_size"] = size
            details["_expected_pass"] = expected_pass
            return ok, details

        return _measure(inner)

    return runner


# --- 10 scenarios: 3 small, 4 medium, 3 large ---


def s01_single_node() -> tuple[bool, dict[str, Any]]:
    graph, origin = build_minimal_scenario()
    pipeline = graph.run_rollback_pipeline({origin})
    ok = pipeline["closure_size"] == 1 and graph.items[origin].excised
    return ok, {"closure_size": pipeline["closure_size"]}


def s02_empty_graph() -> tuple[bool, dict[str, Any]]:
    graph = EpistemicGraph()
    closure = graph.compute_causal_closure(set())
    excision = graph.barrier_ordered_excision(closure)
    ok = len(closure) == 0 and len(excision) == 0
    return ok, {"closure_size": 0}


def s03_cycle_detection() -> tuple[bool, dict[str, Any]]:
    graph = EpistemicGraph()
    graph.agents["a"] = Agent("a", "a")
    graph.add_item(KnowledgeItem("X", "a", "X", ["Y"]))
    graph.add_item(KnowledgeItem("Y", "a", "Y", ["X"]))
    cycles = graph.detect_item_cycles()
    return len(cycles) > 0, {"cycles_found": len(cycles)}


def s04_partial_observability() -> tuple[bool, dict[str, Any]]:
    graph, origin, blind = build_partial_observability_graph()
    graph.agents[blind].local_retraction_registry.clear()
    pipeline = graph.run_rollback_pipeline({origin}, respect_partial_obs=True)
    excised = graph.items["K3_downstream"].excised
    no_local = origin not in graph.agents[blind].local_retraction_registry
    return excised and no_local, {"downstream_excised": excised, "excision_count": pipeline["excised_count"]}


def s05_concurrent_retraction() -> tuple[bool, dict[str, Any]]:
    graph, origins = build_concurrent_contamination_graph()
    pipeline = graph.run_rollback_pipeline(origins)
    expected = {"K_A", "K_B", "K_C", "K_D", "K_E", "K_F", "K_G", "K_H", "K_I"}
    closure = set(pipeline["closure"])
    ok = expected.issubset(closure) and all(graph.items[i].excised for i in expected)
    return ok, {"closure_size": len(closure), "origins": len(origins)}


def s06_adversarial_block() -> tuple[bool, dict[str, Any]]:
    graph, origin, _ = build_partial_observability_graph()
    graph.run_rollback_pipeline({origin})
    attacks = run_adversarial_battery(graph, origin)
    blocked = all(a["blocked"] for a in attacks)
    return blocked and len(attacks) >= 10, {"strategies": len(attacks), "all_blocked": blocked}


def s07_recontamination_reject() -> tuple[bool, dict[str, Any]]:
    graph, origin, _ = build_partial_observability_graph()
    graph.run_rollback_pipeline({origin})
    result = graph.attempt_recontamination(origin, ["K2_derived"], strategy="benchmark")
    return result["blocked"], {"rejection_reasons": len(result.get("rejection_reasons", []))}


def s08_scale_55_agents() -> tuple[bool, dict[str, Any]]:
    graph = build_scale_graph(55, 10, 5)
    pipeline = graph.run_rollback_pipeline({"K0000"})
    chains = sum(1 for it in graph.items.values() if len(it.provenance_chain(graph.items)) >= 4)
    ok = len(graph.agents) >= 50 and len(graph.items) >= 500 and chains >= 100
    return ok and pipeline["excised_count"] >= 1, {
        "agents": len(graph.agents), "items": len(graph.items), "chains": chains,
    }


def s09_perf_500_nodes() -> tuple[bool, dict[str, Any]]:
    graph = build_performance_graph(500)
    origin = "K0000"
    t0 = time.perf_counter()
    closure = graph.compute_causal_closure({origin})
    graph.mark_retracted(origin)
    excision = graph.barrier_ordered_excision(closure)
    replay = graph.replay_from_frontier()
    elapsed = (time.perf_counter() - t0) * 1000
    ok = len(closure) > 100 and len(excision) > 0
    return ok, {"nodes": 500, "closure_size": len(closure), "pipeline_ms": round(elapsed, 2)}


def s10_perf_200_nodes() -> tuple[bool, dict[str, Any]]:
    graph = build_performance_graph(200)
    origin = "K0050"
    pipeline = graph.run_rollback_pipeline({origin})
    return pipeline["closure_size"] >= 50, {
        "nodes": 200, "closure_size": pipeline["closure_size"],
    }


SCENARIOS: list[tuple[str, str, bool, Callable[[], tuple[bool, dict[str, Any]]]]] = [
    ("single_node_rollback", "small", True, s01_single_node),
    ("empty_graph_noop", "small", True, s02_empty_graph),
    ("cycle_detection", "small", True, s03_cycle_detection),
    ("partial_observability_barrier", "medium", True, s04_partial_observability),
    ("concurrent_triple_retraction", "medium", True, s05_concurrent_retraction),
    ("adversarial_10_strategies_blocked", "medium", True, s06_adversarial_block),
    ("recontamination_rejected", "medium", True, s07_recontamination_reject),
    ("scale_55_agents_500_items", "large", True, s08_scale_55_agents),
    ("performance_500_node_closure", "large", True, s09_perf_500_nodes),
    ("performance_200_node_full_pipeline", "large", True, s10_perf_200_nodes),
]


def compute_rates(results: list[ScenarioResult]) -> dict[str, float]:
    total = len(results)
    correct = sum(1 for r in results if r.expected_pass == r.actual_pass)
    fp = sum(1 for r in results if not r.expected_pass and r.actual_pass)
    fn = sum(1 for r in results if r.expected_pass and not r.actual_pass)
    neg = sum(1 for r in results if not r.expected_pass)
    pos = sum(1 for r in results if r.expected_pass)
    return {
        "correctness_rate": round(correct / total, 4) if total else 0.0,
        "false_positive_rate": round(fp / neg, 4) if neg else 0.0,
        "false_negative_rate": round(fn / pos, 4) if pos else 0.0,
        "correct": correct,
        "false_positives": fp,
        "false_negatives": fn,
        "total": total,
    }


def scalability_projection(results: list[ScenarioResult]) -> dict[str, Any]:
    large = [r for r in results if r.size == "large" and r.execution_time_ms > 0]
    if not large:
        large = results
    base_ms = sum(r.execution_time_ms for r in large) / len(large)
    base_items = 500
    return {
        "baseline_ms": round(base_ms, 3),
        "baseline_reference": "mean of large scenarios",
        "assumption": "linear O(n) extrapolation from measured closure/excision times",
        "projections": {
            "10x": round(base_ms * 10, 3),
            "100x": round(base_ms * 100, 3),
            "1000x": round(base_ms * 1000, 3),
        },
        "projected_items": {"10x": base_items * 10, "100x": base_items * 100, "1000x": base_items * 1000},
    }


def run_benchmark() -> dict[str, Any]:
    results: list[ScenarioResult] = []
    for name, size, expected, fn in SCENARIOS:
        runner = _wrap(name, size, expected, fn)
        results.append(runner())

    rates = compute_rates(results)
    scale = scalability_projection(results)
    by_size: dict[str, dict[str, float]] = {}
    for sz in ("small", "medium", "large"):
        subset = [r for r in results if r.size == sz]
        if subset:
            by_size[sz] = {
                "count": len(subset),
                "mean_time_ms": round(sum(r.execution_time_ms for r in subset) / len(subset), 3),
                "mean_memory_kb": round(sum(r.memory_bytes_peak for r in subset) / len(subset) / 1024, 2),
            }

    return {
        "framework": "DERF",
        "harness": "derf_benchmark",
        "author": AUTHOR,
        "orcid": ORCID,
        "disclaimer": DISCLAIMER,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version.split()[0],
        "attack_strategies_available": len(ATTACK_STRATEGIES),
        "scenarios": [
            {
                "name": r.name,
                "size": r.size,
                "expected_pass": r.expected_pass,
                "actual_pass": r.actual_pass,
                "correct": r.expected_pass == r.actual_pass,
                "execution_time_ms": r.execution_time_ms,
                "memory_bytes_peak": r.memory_bytes_peak,
                "memory_kb_peak": round(r.memory_bytes_peak / 1024, 2),
                "details": r.details,
            }
            for r in results
        ],
        "metrics": rates,
        "by_size": by_size,
        "scalability_projection": scale,
        "memory_profile": {
            "largest_scenario": max(results, key=lambda r: r.memory_bytes_peak).name,
            "peak_memory_bytes": max(r.memory_bytes_peak for r in results),
            "peak_memory_kb": round(max(r.memory_bytes_peak for r in results) / 1024, 2),
        },
    }


def print_summary(report: dict[str, Any]) -> None:
    m = report["metrics"]
    s = report["scalability_projection"]
    print("\n" + "=" * 72)
    print("DERF BENCHMARK SUMMARY")
    print("=" * 72)
    print(f"{'SCENARIO':<42} {'SIZE':<8} {'PASS':<6} {'TIME(ms)':>10} {'MEM(KB)':>10}")
    print("-" * 72)
    for sc in report["scenarios"]:
        mark = "OK" if sc["correct"] else "MISS"
        print(
            f"{sc['name']:<42} {sc['size']:<8} {mark:<6} "
            f"{sc['execution_time_ms']:>10.1f} {sc['memory_kb_peak']:>10.1f}"
        )
    print("-" * 72)
    print(f"Correctness rate    : {m['correctness_rate']:.1%} ({m['correct']}/{m['total']})")
    print(f"False positive rate : {m['false_positive_rate']:.1%}")
    print(f"False negative rate : {m['false_negative_rate']:.1%}")
    print(f"\nScalability (baseline {s['baseline_ms']:.1f} ms, {s['assumption']}):")
    for factor in ("10x", "100x", "1000x"):
        proj = s["projections"][factor]
        items = s["projected_items"][factor]
        print(f"  {factor:>5} (~{items} items): {proj:,.1f} ms ({proj / 1000:.2f} s)")
    print("=" * 72)


def main() -> int:
    print("DERF Benchmark Harness")
    print(f"Author: {AUTHOR} (ORCID {ORCID})")
    print(DISCLAIMER)

    report = run_benchmark()
    print_summary(report)

    out_path = Path(__file__).resolve().parent / RESULTS_FILE
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    print(f"\nResults written to: {out_path}")

    return 0 if report["metrics"]["correctness_rate"] == 1.0 else 1


if __name__ == "__main__":
    sys.exit(main())
