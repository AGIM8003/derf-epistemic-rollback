#!/usr/bin/env python3
"""
DERF Proof-of-Concept: Epistemic Rollback with Causal Closure

Author: Agim Haxhijaha, ORCID 0009-0002-3234-7765

DISCLAIMER: This script is a proof-of-concept demonstration only. It is not
production software, has not been peer reviewed, and does not constitute a
formal verification of the DERF framework. Behaviour is simulated for
research illustration purposes.

Library API: `from derf import DERFEngine`
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from derf import Agent, EpistemicGraph, KnowledgeItem

# ---------------------------------------------------------------------------
# Scenario construction
# ---------------------------------------------------------------------------

def build_scenario() -> tuple[EpistemicGraph, str]:
    """
    Build a DAG with 6 agents and provenance chains.
    Returns graph and the contaminated item ID.
    """
    graph = EpistemicGraph()

    # Agent 1: Primary source
    a1 = Agent("agent_source", "Primary Evidence Collector", depends_on=[])
    a1.knowledge["K1_raw_observation"] = KnowledgeItem(
        "K1_raw_observation", "agent_source",
        "Sensor reading: temperature anomaly at node A",
        source_ids=[],
    )
    a1.knowledge["K2_calibration"] = KnowledgeItem(
        "K2_calibration", "agent_source",
        "Calibration certificate valid until 2027",
        source_ids=[],
    )

    # Agent 2: Interpreter (depends on source)
    a2 = Agent("agent_interpreter", "Signal Interpreter", depends_on=["agent_source"])
    a2.knowledge["K3_interpreted"] = KnowledgeItem(
        "K3_interpreted", "agent_interpreter",
        "Anomaly indicates potential fault condition",
        source_ids=["K1_raw_observation", "K2_calibration"],
        derived=True,
    )

    # Agent 3: Corroborator
    a3 = Agent("agent_corroborator", "Independent Corroborator", depends_on=["agent_source"])
    a3.knowledge["K4_corroboration"] = KnowledgeItem(
        "K4_corroboration", "agent_corroborator",
        "Secondary sensor confirms anomaly at node A",
        source_ids=["K1_raw_observation"],
        derived=True,
    )

    # Agent 4: Synthesiser
    a4 = Agent("agent_synthesiser", "Knowledge Synthesiser",
               depends_on=["agent_interpreter", "agent_corroborator"])
    a4.knowledge["K5_synthesis"] = KnowledgeItem(
        "K5_synthesis", "agent_synthesiser",
        "Fault condition confirmed by dual-source agreement",
        source_ids=["K3_interpreted", "K4_corroboration"],
        derived=True,
    )

    # Agent 5: Decision maker
    a5 = Agent("agent_decision", "Decision Authority",
               depends_on=["agent_synthesiser"])
    a5.knowledge["K6_decision"] = KnowledgeItem(
        "K6_decision", "agent_decision",
        "DECISION: Initiate emergency shutdown protocol",
        source_ids=["K5_synthesis"],
        derived=True,
    )

    # Agent 6: Auditor (depends on decision + source)
    a6 = Agent("agent_auditor", "Compliance Auditor",
               depends_on=["agent_decision", "agent_source"])
    a6.knowledge["K7_audit_trail"] = KnowledgeItem(
        "K7_audit_trail", "agent_auditor",
        "Audit record: shutdown decision traceable to source",
        source_ids=["K6_decision", "K2_calibration"],
        derived=True,
    )

    for agent in [a1, a2, a3, a4, a5, a6]:
        graph.add_agent(agent)

    # K1 is the contamination origin (source retracted)
    contaminated_id = "K1_raw_observation"
    return graph, contaminated_id


# ---------------------------------------------------------------------------
# Main demonstration pipeline
# ---------------------------------------------------------------------------

def run_derf_demonstration() -> dict[str, Any]:
    """Execute full DERF pipeline and return evidence log."""
    timestamp = datetime.now(timezone.utc).isoformat()
    graph, contaminated_id = build_scenario()

    evidence: dict[str, Any] = {
        "framework": "DERF",
        "author": "Agim Haxhijaha",
        "orcid": "0009-0002-3234-7765",
        "disclaimer": "PoC only — not production, not peer reviewed",
        "timestamp_utc": timestamp,
        "phases": {},
    }

    # Phase 0: Before state
    before = graph.snapshot()
    evidence["phases"]["0_before"] = before

    print("=" * 70)
    print("DERF PoC: Epistemic Rollback with Causal Closure")
    print(f"Author: Agim Haxhijaha (ORCID 0009-0002-3234-7765)")
    print(f"Timestamp: {timestamp}")
    print("=" * 70)
    print(f"\nInitial state: {len(graph.agents)} agents, {len(graph.items)} knowledge items")

    # Phase 1: Mark contamination
    print(f"\n[1] CONTAMINATION: Retracting source '{contaminated_id}'")
    graph.mark_retracted(contaminated_id)
    evidence["phases"]["1_contamination"] = {
        "retracted_item": contaminated_id,
        "reason": "Primary source retracted by publisher",
    }

    # Phase 2: Causal closure
    print("[2] CAUSAL CLOSURE: Computing downstream dependency closure")
    closure = graph.compute_causal_closure({contaminated_id})
    closure_list = sorted(closure)
    evidence["phases"]["2_causal_closure"] = {
        "origin": contaminated_id,
        "closure_size": len(closure),
        "closure_items": closure_list,
    }
    print(f"    Closure contains {len(closure)} items: {closure_list}")

    # Phase 3: Barrier-ordered excision
    print("[3] BARRIER-ORDERED EXCISION: Removing contaminated items")
    excision_order = graph.barrier_ordered_excision(closure)
    evidence["phases"]["3_excision"] = {
        "order": excision_order,
        "excised_count": len(excision_order),
    }
    print(f"    Excision order: {excision_order}")

    # Phase 4: Clean-frontier replay
    print("[4] CLEAN-FRONTIER REPLAY: Re-deriving from uncontaminated sources")
    replay_results = graph.replay_from_frontier()
    evidence["phases"]["4_replay"] = replay_results
    print(f"    Frontier size: {replay_results['frontier_size']}")
    print(f"    Replayed: {len(replay_results['replayed'])} items")
    print(f"    Unrecoverable: {len(replay_results['unrecoverable'])} items")

    # Phase 5: Recontamination attempt
    print("[5] RECONTAMINATION ATTEMPT: Injecting via alternate path")
    # Try to sneak K1 back through K4 (which depended on K1)
    recontam_result = graph.attempt_recontamination(
        contaminated_id,
        alternate_path=["K4_corroboration"],  # path still traces to K1
    )
    evidence["phases"]["5_recontamination"] = recontam_result

    if recontam_result["blocked"]:
        print("    BLOCKED - recontamination rejected")
        for reason in recontam_result["rejection_reasons"]:
            print(f"      - {reason}")
    else:
        print("    WARNING: Recontamination was NOT blocked (unexpected)")

    # Phase 6: After state
    after = graph.snapshot()
    evidence["phases"]["6_after"] = after

    # Summary
    evidence["summary"] = {
        "contamination_origin": contaminated_id,
        "closure_size": len(closure),
        "excised_count": len(excision_order),
        "replayed_count": len(replay_results["replayed"]),
        "unrecoverable_count": len(replay_results["unrecoverable"]),
        "recontamination_blocked": recontam_result["blocked"],
        "pipeline_success": (
            len(closure) > 1
            and len(excision_order) > 0
            and recontam_result["blocked"]
        ),
    }

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Contamination origin : {contaminated_id}")
    print(f"  Causal closure size  : {len(closure)} items")
    print(f"  Excised              : {len(excision_order)} items")
    print(f"  Replayed             : {len(replay_results['replayed'])} items")
    print(f"  Unrecoverable        : {len(replay_results['unrecoverable'])} items")
    print(f"  Recontamination      : {'BLOCKED' if recontam_result['blocked'] else 'FAILED'}")
    print(f"  Pipeline success     : {evidence['summary']['pipeline_success']}")

    return evidence


def main() -> int:
    evidence = run_derf_demonstration()

    output_path = Path(__file__).resolve().parent / "derf_evidence.json"
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=2, ensure_ascii=False)

    print(f"\nEvidence written to: {output_path}")
    return 0 if evidence["summary"]["pipeline_success"] else 1


if __name__ == "__main__":
    sys.exit(main())

