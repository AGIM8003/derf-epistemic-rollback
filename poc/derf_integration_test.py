#!/usr/bin/env python3
"""DERF public API integration tests."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from derf import DERFEngine

OUT = Path(__file__).with_name("derf_integration_results.json")


def run() -> dict:
    results = []

    # 1 empty
    e = DERFEngine()
    r = e.excise()
    results.append({"name": "empty_input", "pass": r.excised_items == [] and r.clean_items == []})

    # 2 single
    e = DERFEngine()
    e.add_knowledge("solo", sources=[])
    e.mark_contaminated("solo", reason="test")
    r = e.excise()
    results.append({"name": "single_item", "pass": "solo" in r.excised_items})

    # 3 quickstart-like
    e = DERFEngine()
    e.add_knowledge("A", sources=[])
    e.add_knowledge("B", depends_on=["A"])
    e.add_knowledge("C", depends_on=["B"])
    e.add_knowledge("D_clean", sources=[])
    e.mark_contaminated("A")
    r = e.excise()
    results.append({
        "name": "typical_cascade",
        "pass": set(r.excised_items) >= {"A", "B", "C"} and "D_clean" in r.clean_items,
    })

    # 4 large-scale
    e = DERFEngine()
    e.add_knowledge("R0", sources=[])
    for i in range(1, 120):
        e.add_knowledge(f"R{i}", depends_on=[f"R{i-1}"])
    e.mark_contaminated("R0")
    r = e.excise()
    results.append({"name": "large_scale_120", "pass": r.closure_size == 120 and len(r.excised_items) == 120})

    # 5 errors
    ok_err = True
    e = DERFEngine()
    e.add_knowledge("X", sources=[])
    try:
        e.add_knowledge("X", sources=[])
        ok_err = False
    except ValueError:
        pass
    try:
        e.add_knowledge("Y", depends_on=["Y"])
        ok_err = False
    except ValueError:
        pass
    try:
        e.mark_contaminated("missing")
        ok_err = False
    except ValueError:
        pass
    results.append({"name": "error_handling", "pass": ok_err})

    # 6 leaf contamination
    e = DERFEngine()
    e.add_knowledge("root", sources=[])
    e.add_knowledge("leaf", depends_on=["root"])
    e.mark_contaminated("leaf")
    r = e.excise()
    results.append({
        "name": "contamination_no_dependents",
        "pass": r.excised_items == ["leaf"] and "root" in r.clean_items,
    })

    return {
        "framework": "DERF",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "pass": all(x["pass"] for x in results),
    }


def main() -> int:
    evidence = run()
    OUT.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"DERF integration pass={evidence['pass']} ({sum(1 for r in evidence['results'] if r['pass'])}/{len(evidence['results'])})")
    return 0 if evidence["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
