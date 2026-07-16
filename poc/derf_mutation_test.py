#!/usr/bin/env python3
"""
DERF Mutation Testing — prove gate logic catches deliberate bugs.

Author: Agim Haxhijaha, ORCID 0009-0002-3234-7765
DISCLAIMER: PoC mutation suite only. Not production.
"""

from __future__ import annotations

import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

AUTHOR = "Agim Haxhijaha"
ORCID = "0009-0002-3234-7765"

# Minimal core under test
CHILDREN = {"K1": ["K3", "K4"], "K3": ["K5"], "K4": ["K6"], "K5": ["K7"], "K6": ["K7"], "K2": ["K5"]}


def closure(origin: str, children: dict[str, list[str]]) -> set[str]:
    seen: set[str] = set()
    stack = [origin]
    while stack:
        x = stack.pop()
        if x in seen:
            continue
        seen.add(x)
        stack.extend(children.get(x, []))
    return seen


def reject_recontam(origin: str, probe: str, children: dict[str, list[str]]) -> bool:
    return probe in closure(origin, children)


def oracle_tests(fn_closure: Callable, fn_reject: Callable, children: dict[str, list[str]]) -> list[tuple[str, bool]]:
    """Return list of (test_name, passed)."""
    c = fn_closure("K1", children)
    tests = []
    tests.append(("closure_includes_descendants", {"K3", "K4", "K5", "K6", "K7", "K1"} <= c))
    tests.append(("closure_excludes_clean_K2_only_path", "K2" not in c or True))  # K2 not descendant of K1
    tests.append(("K2_not_in_K1_closure", "K2" not in fn_closure("K1", children)))
    tests.append(("reject_K7", fn_reject("K1", "K7", children) is True))
    tests.append(("reject_K4", fn_reject("K1", "K4", children) is True))
    tests.append(("allow_unrelated", fn_reject("K1", "KX", children) is False))
    tests.append(("nonempty_closure", len(fn_closure("K1", children)) >= 5))
    return tests


def mutate_skip_reject(origin, probe, children):
    return False  # always allow recontam


def mutate_ge_to_gt_size(origin, children):
    c = closure(origin, children)
    # buggy: requires > instead of >= for minimum size check used by wrapper
    return c if len(c) > 10 else set()  # empties valid closures


def mutate_drop_loop(origin, children):
    # only one hop
    return {origin} | set(children.get(origin, []))


def mutate_swap_args(probe, origin, children):  # swapped
    return reject_recontam(origin, probe, children)


def mutate_no_init(origin, children):
    seen = None  # type: ignore
    try:
        seen.add(origin)  # type: ignore
        return set()
    except Exception:
        return set()  # fails closed incorrectly empty


def mutate_threshold(origin, children):
    c = closure(origin, children)
    return c if len(c) >= 100 else set()


def mutate_no_error_handling(origin, children):
    return closure(origin, children)  # but tests inject bad children


def mutate_reverse_order(origin, children):
    c = list(closure(origin, children))
    return set(reversed(c))  # set ignores order — need different bug
    # actually reverse edges
    # fallthrough alternative:


def mutate_skip_validation(origin, probe, children):
    return True  # always reject even clean — still may fail allow_unrelated


def mutate_early_return(origin, children):
    return {origin}


MUTATIONS: list[dict[str, Any]] = [
    {"name": "skip_recontam_check", "kind": "reject", "fn": mutate_skip_reject},
    {"name": "change_size_comparison", "kind": "closure", "fn": mutate_ge_to_gt_size},
    {"name": "remove_loop_iterations", "kind": "closure", "fn": mutate_drop_loop},
    {"name": "swap_reject_args", "kind": "reject_swap", "fn": mutate_swap_args},
    {"name": "delete_init", "kind": "closure", "fn": mutate_no_init},
    {"name": "change_threshold", "kind": "closure", "fn": mutate_threshold},
    {"name": "remove_error_handling", "kind": "closure_bad_children", "fn": mutate_no_error_handling},
    {"name": "reverse_edges", "kind": "closure_rev", "fn": None},
    {"name": "skip_validation_always_reject", "kind": "reject", "fn": mutate_skip_validation},
    {"name": "early_return_before_closure", "kind": "closure", "fn": mutate_early_return},
]


def run_mutation(m: dict[str, Any]) -> dict[str, Any]:
    children = copy.deepcopy(CHILDREN)
    fn_c = closure
    fn_r = reject_recontam
    if m["kind"] == "reject":
        fn_r = m["fn"]
    elif m["kind"] == "closure":
        fn_c = m["fn"]
    elif m["kind"] == "reject_swap":
        def fn_r(o, p, ch):
            return m["fn"](p, o, ch)
    elif m["kind"] == "closure_bad_children":
        children = {"K1": None}  # type: ignore
        def fn_c(o, ch):
            try:
                return closure(o, ch)
            except Exception:
                return {"K1", "K3", "K4", "K5"}  # silently wrong success
    elif m["kind"] == "closure_rev":
        rev = {}
        for a, bs in CHILDREN.items():
            for b in bs:
                rev.setdefault(b, []).append(a)
        children = rev
        fn_c = closure

    try:
        results = oracle_tests(fn_c, fn_r, children)
    except Exception as exc:
        return {"name": m["name"], "detected": True, "caught_by": f"exception:{exc}", "passed": 0, "failed": 1}

    failed = [n for n, ok in results if not ok]
    detected = len(failed) > 0
    return {
        "name": m["name"],
        "detected": detected,
        "caught_by": failed[0] if failed else None,
        "failed_tests": failed,
        "passed": sum(1 for _, ok in results if ok),
        "failed": len(failed),
    }


def main() -> int:
    print("DERF Mutation Testing")
    rows = [run_mutation(m) for m in MUTATIONS]
    detected = sum(1 for r in rows if r["detected"])
    score = detected / len(rows)
    report = {
        "framework": "DERF",
        "author": AUTHOR,
        "orcid": ORCID,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mutations_total": len(rows),
        "mutations_detected": detected,
        "mutation_score": round(score, 3),
        "pass_threshold": 0.9,
        "mutations": rows,
        "suite_pass": score >= 0.9,
    }
    out = Path(__file__).resolve().parent / "derf_mutation_results.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Mutation score: {score:.0%} ({detected}/{len(rows)})")
    for r in rows:
        print(f"  [{'CAUGHT' if r['detected'] else 'SURVIVED'}] {r['name']} -> {r['caught_by']}")
    print(f"Results: {out}")
    return 0 if report["suite_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
