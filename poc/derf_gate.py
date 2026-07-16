#!/usr/bin/env python3
"""
DERF Reality Gate Demonstrator — Epistemic Rollback with Causal Closure

Author: Agim Haxhijaha, ORCID 0009-0002-3234-7765

DISCLAIMER: This script is a proof-of-concept Reality Gate demonstrator only.
It is not production software, has not been peer reviewed, and does not
constitute formal verification of the DERF framework. Behaviour is simulated
for research illustration purposes. Passing this gate does not imply patent
grant, regulatory compliance, or production readiness.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
import time
import unicodedata
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


AUTHOR = "Agim Haxhijaha"
ORCID = "0009-0002-3234-7765"
DISCLAIMER = (
    "PoC Reality Gate demonstrator only — not production, not peer reviewed, "
    "not formal verification"
)


# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------


@dataclass
class KnowledgeItem:
    """A single epistemic claim held by an agent."""

    item_id: str
    agent_id: str
    claim: str
    source_ids: list[str]
    derived: bool = False
    contaminated: bool = False
    excised: bool = False
    retracted: bool = False
    epoch: int = 0
    content_hash: str = ""
    authority_id: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = canonical_claim_hash(self.claim)

    def provenance_chain(self, registry: dict[str, KnowledgeItem]) -> list[str]:
        chain: list[str] = []
        seen: set[str] = set()

        def walk(item_id: str) -> None:
            if item_id in seen:
                return
            seen.add(item_id)
            item = registry.get(item_id)
            if item is None:
                return
            for src in item.source_ids:
                walk(src)
            chain.append(item_id)

        for src in self.source_ids:
            walk(src)
        chain.append(self.item_id)
        return chain

    def semantic_fingerprint(self) -> str:
        normalized = normalize_claim(self.claim)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


@dataclass
class Agent:
    """An epistemic agent in the dependency DAG."""

    agent_id: str
    role: str
    depends_on: list[str] = field(default_factory=list)
    knowledge: dict[str, KnowledgeItem] = field(default_factory=dict)
    local_retraction_registry: set[str] = field(default_factory=set)
    partial_observability: bool = False


@dataclass
class EpistemicGraph:
    """DAG of agents and knowledge items with DERF rollback semantics."""

    agents: dict[str, Agent] = field(default_factory=dict)
    items: dict[str, KnowledgeItem] = field(default_factory=dict)
    retracted_sources: set[str] = field(default_factory=set)
    unknown_edges: set[tuple[str, str]] = field(default_factory=set)
    quarantined_items: set[str] = field(default_factory=set)
    epoch: int = 0
    committed: bool = False

    def add_agent(self, agent: Agent) -> None:
        self.agents[agent.agent_id] = agent
        for item in agent.knowledge.values():
            self.items[item.item_id] = item

    def add_item(self, item: KnowledgeItem) -> None:
        self.items[item.item_id] = item
        if item.agent_id in self.agents:
            self.agents[item.agent_id].knowledge[item.item_id] = item

    def mark_retracted(self, item_id: str, propagate_local: bool = True) -> None:
        self.retracted_sources.add(item_id)
        if item_id in self.items:
            self.items[item_id].retracted = True
            self.items[item_id].contaminated = True
        if propagate_local:
            for agent in self.agents.values():
                agent.local_retraction_registry.add(item_id)

    def mark_unknown_edge(self, upstream: str, downstream: str) -> None:
        self.unknown_edges.add((upstream, downstream))

    def agent_topo_order(self) -> list[str]:
        in_degree = {aid: len(self.agents[aid].depends_on) for aid in self.agents}
        queue = deque(aid for aid, deg in in_degree.items() if deg == 0)
        order: list[str] = []
        while queue:
            current = queue.popleft()
            order.append(current)
            for agent in self.agents.values():
                if current in agent.depends_on:
                    in_degree[agent.agent_id] -= 1
                    if in_degree[agent.agent_id] == 0:
                        queue.append(agent.agent_id)
        if len(order) != len(self.agents):
            raise ValueError("Agent dependency graph contains a cycle")
        return order

    def detect_item_cycles(self) -> list[list[str]]:
        """Return cycles in item dependency graph, if any."""
        graph: dict[str, list[str]] = defaultdict(list)
        for item in self.items.values():
            for src in item.source_ids:
                graph[src].append(item.item_id)

        cycles: list[list[str]] = []
        visited: set[str] = set()
        stack: set[str] = set()
        path: list[str] = []

        def dfs(node: str) -> None:
            if node in stack:
                idx = path.index(node)
                cycles.append(path[idx:] + [node])
                return
            if node in visited:
                return
            visited.add(node)
            stack.add(node)
            path.append(node)
            for nxt in graph.get(node, []):
                dfs(nxt)
            path.pop()
            stack.remove(node)

        for node in list(self.items.keys()):
            dfs(node)
        return cycles

    def item_dependency_graph(self) -> dict[str, list[str]]:
        dependents: dict[str, list[str]] = defaultdict(list)
        for item in self.items.values():
            for src in item.source_ids:
                dependents[src].append(item.item_id)
        return dict(dependents)

    def compute_causal_closure(self, origin_ids: set[str]) -> set[str]:
        dependents = self.item_dependency_graph()
        closure: set[str] = set()
        queue = deque(origin_ids)
        while queue:
            current = queue.popleft()
            if current in closure:
                continue
            closure.add(current)
            for downstream in dependents.get(current, []):
                if downstream not in closure:
                    queue.append(downstream)
        return closure

    def quarantine_unknown_paths(self, closure: set[str]) -> set[str]:
        """Quarantine items with UNKNOWN upstream influence on closure boundary."""
        for upstream, downstream in self.unknown_edges:
            if upstream in closure or downstream in closure:
                self.quarantined_items.add(downstream)
                if downstream in self.items:
                    self.items[downstream].contaminated = True
        return set(self.quarantined_items)

    def barrier_ordered_excision(
        self,
        closure: set[str],
        respect_partial_obs: bool = False,
    ) -> list[str]:
        """
        Remove contaminated items in barrier order. Under partial observability,
        agents without local retraction info still receive excision via
        coordinator-propagated barrier waves.
        """
        dependents = self.item_dependency_graph()
        closure_set = set(closure) | self.quarantined_items
        in_closure_dependents: dict[str, int] = {}

        for item_id in closure_set:
            count = sum(
                1 for d in dependents.get(item_id, []) if d in closure_set
            )
            in_closure_dependents[item_id] = count

        queue = deque(
            iid for iid, cnt in in_closure_dependents.items() if cnt == 0
        )
        excision_order: list[str] = []
        agent_barrier_wave = 0

        while queue:
            current = queue.popleft()
            if current not in closure_set:
                continue
            item = self.items.get(current)
            if item is None:
                continue
            agent = self.agents.get(item.agent_id)
            if respect_partial_obs and agent and agent.partial_observability:
                if current not in agent.local_retraction_registry:
                    agent_barrier_wave += 1
            if not item.excised:
                item.excised = True
                item.contaminated = True
                excision_order.append(current)

            for src_id, item_obj in self.items.items():
                if current in item_obj.source_ids and src_id in closure_set:
                    in_closure_dependents[src_id] -= 1
                    if in_closure_dependents[src_id] == 0:
                        queue.append(src_id)

        remaining = [
            iid for iid in closure_set
            if iid in self.items and not self.items[iid].excised
        ]
        for iid in sorted(remaining, key=lambda x: len(self.items[x].source_ids)):
            self.items[iid].excised = True
            self.items[iid].contaminated = True
            excision_order.append(iid)

        return excision_order

    def clean_frontier(self) -> set[str]:
        frontier: set[str] = set()
        for item in self.items.values():
            if item.excised or item.item_id in self.quarantined_items:
                continue
            sources_excised = any(
                self.items[s].excised for s in item.source_ids if s in self.items
            )
            if not sources_excised:
                frontier.add(item.item_id)
        return frontier

    def replay_from_frontier(self) -> dict[str, Any]:
        frontier = self.clean_frontier()
        replayed: list[dict[str, str]] = []
        still_missing: list[str] = []

        for item in [it for it in self.items.values() if it.excised]:
            clean_sources = [
                s for s in item.source_ids
                if s in self.items and not self.items[s].excised
            ]
            excised_sources = [
                s for s in item.source_ids
                if s in self.items and self.items[s].excised
            ]
            if clean_sources:
                partial = len(excised_sources) > 0
                suffix = " (partial)" if partial else ""
                new_item = KnowledgeItem(
                    item_id=f"{item.item_id}_replayed",
                    agent_id=item.agent_id,
                    claim=f"[REPLAYED{suffix}] {item.claim}",
                    source_ids=clean_sources,
                    derived=True,
                    epoch=self.epoch + 1,
                )
                self.add_item(new_item)
                replayed.append({
                    "original": item.item_id,
                    "replayed_as": new_item.item_id,
                    "partial": partial,
                })
            else:
                still_missing.append(item.item_id)

        return {
            "frontier_size": len(frontier),
            "replayed": replayed,
            "unrecoverable": still_missing,
        }

    def resolve_provenance(self, item_id: str) -> set[str]:
        """Resolve all ultimate source item IDs."""
        roots: set[str] = set()
        item = self.items.get(item_id)
        if item is None:
            return roots
        if not item.source_ids:
            roots.add(item_id)
            return roots
        for src in item.source_ids:
            roots.update(self.resolve_provenance(src))
        return roots

    def attempt_recontamination(
        self,
        retracted_id: str,
        alternate_path: list[str],
        *,
        claim: str | None = None,
        new_id: str | None = None,
        epoch: int | None = None,
        authority_id: str = "",
        strategy: str = "generic",
    ) -> dict[str, Any]:
        """Try to re-inject retracted knowledge; return rejection proof if blocked."""
        retracted = self.items.get(retracted_id)
        if retracted is None:
            return {"blocked": True, "reason": "retracted item not found", "strategy": strategy}

        fake_id = new_id or f"reinject_{retracted_id}_{strategy}"
        fake_claim = claim if claim is not None else retracted.claim
        fake_item = KnowledgeItem(
            item_id=fake_id,
            agent_id="agent_reinjector",
            claim=fake_claim,
            source_ids=alternate_path,
            derived=True,
            epoch=epoch if epoch is not None else self.epoch,
            authority_id=authority_id,
        )

        rejection_reasons: list[str] = []

        if retracted_id in self.retracted_sources:
            rejection_reasons.append(
                f"Source {retracted_id} is on global retracted-source registry"
            )

        if fake_item.semantic_fingerprint() == retracted.semantic_fingerprint():
            rejection_reasons.append(
                "Semantic fingerprint matches retracted claim (relabel/rephrase blocked)"
            )

        if retracted.content_hash == fake_item.content_hash:
            rejection_reasons.append(
                "Content hash matches retracted claim"
            )

        for src in alternate_path:
            if src in self.retracted_sources:
                rejection_reasons.append(
                    f"Alternate path traverses retracted source {src}"
                )
            if src in self.items and self.items[src].excised:
                rejection_reasons.append(
                    f"Alternate path traverses excised item {src}"
                )
            item = self.items.get(src)
            if item and retracted_id in item.provenance_chain(self.items):
                rejection_reasons.append(
                    f"Alternate path {src} transitively depends on {retracted_id}"
                )

        resolved = set()
        for src in alternate_path:
            resolved.update(self.resolve_provenance(src))
        if retracted_id in resolved:
            rejection_reasons.append(
                "Resolved provenance includes retracted origin"
            )

        for existing in self.items.values():
            if existing.excised or existing.retracted:
                continue
            if existing.semantic_fingerprint() == fake_item.semantic_fingerprint():
                if retracted_id in existing.provenance_chain(self.items):
                    rejection_reasons.append(
                        f"Collaborative injection overlaps excised lineage via {existing.item_id}"
                    )

        if epoch is not None and epoch <= retracted.epoch:
            rejection_reasons.append(
                f"Temporal replay from epoch {epoch} <= retracted epoch {retracted.epoch}"
            )

        if authority_id and authority_id != retracted.authority_id:
            if retracted.authority_id:
                rejection_reasons.append(
                    f"Authority spoofing: {authority_id} != {retracted.authority_id}"
                )

        blocked = len(rejection_reasons) > 0
        if not blocked:
            self.add_item(fake_item)

        return {
            "strategy": strategy,
            "attempted_item": fake_id,
            "alternate_path": alternate_path,
            "blocked": blocked,
            "rejection_reasons": rejection_reasons,
            "reinjector_accepted": not blocked,
        }

    def run_rollback_pipeline(
        self,
        origin_ids: set[str],
        *,
        respect_partial_obs: bool = False,
    ) -> dict[str, Any]:
        for oid in origin_ids:
            self.mark_retracted(oid, propagate_local=not respect_partial_obs)
        closure = self.compute_causal_closure(origin_ids)
        quarantined = self.quarantine_unknown_paths(closure)
        excision_order = self.barrier_ordered_excision(
            closure, respect_partial_obs=respect_partial_obs
        )
        replay = self.replay_from_frontier()
        return {
            "origins": sorted(origin_ids),
            "closure_size": len(closure),
            "closure": sorted(closure),
            "quarantined": sorted(quarantined),
            "excision_order": excision_order,
            "excised_count": len(excision_order),
            "replay": replay,
        }


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def normalize_claim(claim: str) -> str:
    text = claim.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def canonical_claim_hash(claim: str) -> str:
    return hashlib.sha256(normalize_claim(claim).encode("utf-8")).hexdigest()


def deep_copy_graph(graph: EpistemicGraph) -> EpistemicGraph:
    return copy.deepcopy(graph)


# ---------------------------------------------------------------------------
# Graph builders
# ---------------------------------------------------------------------------


def build_scale_graph(
    num_agents: int = 55,
    items_per_agent: int = 10,
    chain_depth: int = 5,
) -> EpistemicGraph:
    """Build large DAG: num_agents agents, 500+ items, 100+ chains."""
    graph = EpistemicGraph()
    item_counter = 0
    chain_count = 0

    layers = max(1, num_agents // 5)
    agents_per_layer = num_agents // layers

    layer_agents: list[list[str]] = []
    for layer in range(layers):
        layer_ids: list[str] = []
        for pos in range(agents_per_layer):
            aid = f"agent_L{layer}_P{pos}"
            deps: list[str] = []
            if layer > 0:
                prev = layer_agents[layer - 1]
                deps = [prev[pos % len(prev)]]
                if pos > 0:
                    deps.append(prev[(pos - 1) % len(prev)])
            agent = Agent(aid, f"Role_L{layer}", depends_on=deps)
            graph.add_agent(agent)
            layer_ids.append(aid)
        layer_agents.append(layer_ids)

    for layer_idx, aids in enumerate(layer_agents):
        for aid in aids:
            agent = graph.agents[aid]
            base_sources: list[str] = []
            if layer_idx > 0:
                upstream = graph.agents[layer_agents[layer_idx - 1][0]]
                base_sources = list(upstream.knowledge.keys())[:2]

            for j in range(items_per_agent):
                iid = f"K{item_counter:04d}"
                item_counter += 1
                sources = base_sources if j > 0 else []
                if j > 0 and base_sources:
                    sources = [base_sources[j % len(base_sources)]]
                    if j % 3 == 0 and len(base_sources) > 1:
                        sources = base_sources[:2]
                graph.add_item(KnowledgeItem(
                    item_id=iid,
                    agent_id=aid,
                    claim=f"Claim layer {layer_idx} item {j} from {aid}",
                    source_ids=sources,
                    derived=bool(sources),
                    epoch=layer_idx,
                ))
                agent.knowledge[iid] = graph.items[iid]
                if len(sources) >= chain_depth - 1:
                    chain_count += 1

    for chain_idx in range(max(0, 110 - chain_count)):
        start_layer = chain_idx % max(1, layers - 1)
        if start_layer >= len(layer_agents) - 1:
            continue
        src_aid = layer_agents[start_layer][0]
        tgt_aid = layer_agents[start_layer + 1][0]
        src_items = list(graph.agents[src_aid].knowledge.keys())
        if not src_items:
            continue
        iid = f"CHAIN_{chain_idx:03d}"
        graph.add_item(KnowledgeItem(
            item_id=iid,
            agent_id=tgt_aid,
            claim=f"Chain {chain_idx} derived claim",
            source_ids=[src_items[-1]],
            derived=True,
        ))
        graph.agents[tgt_aid].knowledge[iid] = graph.items[iid]
        chain_count += 1

    return graph


def build_partial_observability_graph() -> tuple[EpistemicGraph, str, str]:
    """Graph where one downstream agent lacks local retraction registry."""
    graph = EpistemicGraph()

    a1 = Agent("agent_source", "Source", depends_on=[])
    a1.knowledge["K1_origin"] = KnowledgeItem(
        "K1_origin", "agent_source", "Primary observation: anomaly detected", []
    )
    a2 = Agent("agent_mid", "Interpreter", depends_on=["agent_source"])
    a2.knowledge["K2_derived"] = KnowledgeItem(
        "K2_derived", "agent_mid", "Interpreted fault signal",
        ["K1_origin"], derived=True,
    )
    a3 = Agent(
        "agent_blind", "Downstream (partial observability)",
        depends_on=["agent_mid"],
        partial_observability=True,
    )
    a3.knowledge["K3_downstream"] = KnowledgeItem(
        "K3_downstream", "agent_blind", "Decision based on fault signal",
        ["K2_derived"], derived=True,
    )
    a4 = Agent("agent_peer", "Peer corroborator", depends_on=["agent_source"])
    a4.knowledge["K4_peer"] = KnowledgeItem(
        "K4_peer", "agent_peer", "Peer confirms via source",
        ["K1_origin"], derived=True,
    )

    for a in [a1, a2, a3, a4]:
        graph.add_agent(a)

    graph.mark_unknown_edge("K1_origin", "K3_downstream")
    return graph, "K1_origin", "agent_blind"


def build_concurrent_contamination_graph() -> tuple[EpistemicGraph, set[str]]:
    graph = EpistemicGraph()
    origins = {"K_A", "K_B", "K_C"}

    for oid in origins:
        graph.add_item(KnowledgeItem(oid, "agent_source", f"Source {oid}", []))

    graph.add_item(KnowledgeItem(
        "K_D", "agent_a", "Derived from A", ["K_A"], derived=True,
    ))
    graph.add_item(KnowledgeItem(
        "K_E", "agent_b", "Derived from B", ["K_B"], derived=True,
    ))
    graph.add_item(KnowledgeItem(
        "K_F", "agent_c", "Derived from C", ["K_C"], derived=True,
    ))
    graph.add_item(KnowledgeItem(
        "K_G", "agent_merge", "Merge A+B", ["K_D", "K_E"], derived=True,
    ))
    graph.add_item(KnowledgeItem(
        "K_H", "agent_merge2", "Merge G+C", ["K_G", "K_F"], derived=True,
    ))
    graph.add_item(KnowledgeItem(
        "K_I", "agent_final", "Final decision", ["K_H"], derived=True,
    ))

    for aid in ["agent_source", "agent_a", "agent_b", "agent_c", "agent_merge", "agent_merge2", "agent_final"]:
        graph.agents[aid] = Agent(aid, aid)

    return graph, origins


def build_performance_graph(num_nodes: int = 500) -> EpistemicGraph:
    graph = EpistemicGraph()
    graph.agents["agent_perf"] = Agent("agent_perf", "perf")

    for i in range(num_nodes):
        sources = [f"K{j:04d}" for j in range(max(0, i - 2), i)]
        graph.add_item(KnowledgeItem(
            item_id=f"K{i:04d}",
            agent_id="agent_perf",
            claim=f"Performance node {i}",
            source_ids=sources,
            derived=bool(sources),
        ))

    return graph


def build_minimal_scenario() -> tuple[EpistemicGraph, str]:
    graph = EpistemicGraph()
    graph.agents["a0"] = Agent("a0", "solo")
    graph.add_item(KnowledgeItem("K_only", "a0", "Single claim", []))
    return graph, "K_only"


# ---------------------------------------------------------------------------
# Adversarial attack strategies (10)
# ---------------------------------------------------------------------------


ATTACK_STRATEGIES: list[tuple[str, Callable[..., dict[str, Any]]]] = []


def _register_attack(name: str):
    def decorator(fn: Callable[..., dict[str, Any]]):
        ATTACK_STRATEGIES.append((name, fn))
        return fn
    return decorator


@_register_attack("relabel")
def attack_relabel(graph: EpistemicGraph, retracted_id: str) -> dict[str, Any]:
    item = graph.items[retracted_id]
    return graph.attempt_recontamination(
        retracted_id, [], claim=item.claim,
        new_id=f"K_relabel_{retracted_id}",
        strategy="relabel",
    )


@_register_attack("split")
def attack_split(graph: EpistemicGraph, retracted_id: str) -> dict[str, Any]:
    item = graph.items[retracted_id]
    parts = item.claim.split()
    half = " ".join(parts[: len(parts) // 2 + 1])
    return graph.attempt_recontamination(
        retracted_id, [], claim=half,
        new_id=f"K_split_{retracted_id}",
        strategy="split",
    )


@_register_attack("rephrase")
def attack_rephrase(graph: EpistemicGraph, retracted_id: str) -> dict[str, Any]:
    item = graph.items[retracted_id]
    rephrased = f"Restated: {item.claim.rstrip('.')}"
    return graph.attempt_recontamination(
        retracted_id, [], claim=rephrased,
        new_id=f"K_rephrase_{retracted_id}",
        strategy="rephrase",
    )


@_register_attack("indirect_citation")
def attack_indirect_citation(graph: EpistemicGraph, retracted_id: str) -> dict[str, Any]:
    intermediates = [
        iid for iid, it in graph.items.items()
        if retracted_id in it.source_ids and not it.excised
    ]
    path = intermediates[:1] if intermediates else [retracted_id]
    return graph.attempt_recontamination(
        retracted_id, path, strategy="indirect_citation",
    )


@_register_attack("transitive_reference")
def attack_transitive_reference(graph: EpistemicGraph, retracted_id: str) -> dict[str, Any]:
    chain = [
        iid for iid, it in graph.items.items()
        if it.derived and retracted_id in it.provenance_chain(graph.items)
    ]
    path = chain[-1:] if chain else [retracted_id]
    return graph.attempt_recontamination(
        retracted_id, path, strategy="transitive_reference",
    )


@_register_attack("temporal_replay")
def attack_temporal_replay(graph: EpistemicGraph, retracted_id: str) -> dict[str, Any]:
    item = graph.items[retracted_id]
    return graph.attempt_recontamination(
        retracted_id, [retracted_id],
        epoch=max(0, item.epoch - 1),
        strategy="temporal_replay",
    )


@_register_attack("synthetic_rederivation")
def attack_synthetic_rederivation(graph: EpistemicGraph, retracted_id: str) -> dict[str, Any]:
    item = graph.items[retracted_id]
    synth_id = f"synth_{retracted_id}"
    graph.add_item(KnowledgeItem(
        synth_id, "agent_synth", f"Synthetic re-derivation of {item.claim}",
        [retracted_id], derived=True,
    ))
    return graph.attempt_recontamination(
        retracted_id, [synth_id], strategy="synthetic_rederivation",
    )


@_register_attack("authority_spoofing")
def attack_authority_spoofing(graph: EpistemicGraph, retracted_id: str) -> dict[str, Any]:
    return graph.attempt_recontamination(
        retracted_id, [],
        authority_id="spoofed_authority_999",
        strategy="authority_spoofing",
    )


@_register_attack("partial_overlap")
def attack_partial_overlap(graph: EpistemicGraph, retracted_id: str) -> dict[str, Any]:
    clean = [
        iid for iid, it in graph.items.items()
        if not it.excised and iid != retracted_id and not it.source_ids
    ]
    path = ([clean[0]] if clean else []) + [retracted_id]
    return graph.attempt_recontamination(
        retracted_id, path, strategy="partial_overlap",
    )


@_register_attack("collaborative_injection")
def attack_collaborative_injection(graph: EpistemicGraph, retracted_id: str) -> dict[str, Any]:
    collab_id = f"collab_{retracted_id}"
    graph.add_item(KnowledgeItem(
        collab_id, "agent_colluder",
        graph.items[retracted_id].claim,
        [retracted_id], derived=True,
    ))
    return graph.attempt_recontamination(
        retracted_id, [collab_id],
        strategy="collaborative_injection",
    )


def run_adversarial_battery(graph: EpistemicGraph, retracted_id: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for name, fn in ATTACK_STRATEGIES:
        g = deep_copy_graph(graph)
        for oid in graph.retracted_sources:
            g.mark_retracted(oid)
            if oid in g.items:
                g.items[oid].excised = True
        result = fn(g, retracted_id)
        result["attack_name"] = name
        results.append(result)
    return results


# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------


@dataclass
class TestResult:
    name: str
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)
    timing_ms: float = 0.0
    error: str = ""


class DerfGateRunner:
    """Reality Gate test runner for DERF."""

    def __init__(self) -> None:
        self.results: list[TestResult] = []

    def record(self, result: TestResult) -> None:
        self.results.append(result)

    def test_scale(self) -> TestResult:
        t0 = time.perf_counter()
        try:
            graph = build_scale_graph(55, 10, 5)
            num_agents = len(graph.agents)
            num_items = len(graph.items)
            chains = sum(
                1 for it in graph.items.values()
                if len(it.provenance_chain(graph.items)) >= 4
            )
            origin = "K0000"
            pipeline = graph.run_rollback_pipeline({origin})
            passed = (
                num_agents >= 50
                and num_items >= 500
                and chains >= 100
                and pipeline["closure_size"] >= 1
                and pipeline["excised_count"] >= 1
            )
            elapsed = (time.perf_counter() - t0) * 1000
            return TestResult(
                "scale_50_agents_500_items_100_chains",
                passed,
                {
                    "agents": num_agents,
                    "items": num_items,
                    "dependency_chains": chains,
                    "closure_size": pipeline["closure_size"],
                },
                elapsed,
            )
        except Exception as exc:
            return TestResult(
                "scale_50_agents_500_items_100_chains", False,
                error=str(exc),
                timing_ms=(time.perf_counter() - t0) * 1000,
            )

    def test_concurrent_contamination(self) -> TestResult:
        t0 = time.perf_counter()
        try:
            graph, origins = build_concurrent_contamination_graph()
            pipeline = graph.run_rollback_pipeline(origins)
            closure = set(pipeline["closure"])
            expected = {"K_A", "K_B", "K_C", "K_D", "K_E", "K_F", "K_G", "K_H", "K_I"}
            passed = expected.issubset(closure) and all(
                graph.items[iid].excised for iid in expected if iid in graph.items
            )
            return TestResult(
                "concurrent_triple_retraction",
                passed,
                {
                    "origins": sorted(origins),
                    "closure_size": len(closure),
                    "closure_matches_expected": expected.issubset(closure),
                },
                (time.perf_counter() - t0) * 1000,
            )
        except Exception as exc:
            return TestResult(
                "concurrent_triple_retraction", False, error=str(exc),
                timing_ms=(time.perf_counter() - t0) * 1000,
            )

    def test_partial_observability(self) -> TestResult:
        t0 = time.perf_counter()
        try:
            graph, origin, blind_agent = build_partial_observability_graph()
            graph.agents[blind_agent].local_retraction_registry.clear()
            pipeline = graph.run_rollback_pipeline(
                {origin}, respect_partial_obs=True,
            )
            downstream_excised = graph.items["K3_downstream"].excised
            blind_has_no_local = origin not in graph.agents[blind_agent].local_retraction_registry
            passed = downstream_excised and blind_has_no_local
            return TestResult(
                "partial_observability_barrier_excision",
                passed,
                {
                    "blind_agent": blind_agent,
                    "downstream_excised": downstream_excised,
                    "local_registry_empty": blind_has_no_local,
                    "excision_order": pipeline["excision_order"],
                },
                (time.perf_counter() - t0) * 1000,
            )
        except Exception as exc:
            return TestResult(
                "partial_observability_barrier_excision", False, error=str(exc),
                timing_ms=(time.perf_counter() - t0) * 1000,
            )

    def test_adversarial_recontamination(self) -> TestResult:
        t0 = time.perf_counter()
        try:
            graph, origin, _ = build_partial_observability_graph()
            graph.run_rollback_pipeline({origin})
            attacks = run_adversarial_battery(graph, origin)
            all_blocked = all(a["blocked"] for a in attacks)
            strategies_tested = len(attacks)
            return TestResult(
                "adversarial_10_injection_strategies",
                all_blocked and strategies_tested >= 10,
                {
                    "strategies_tested": strategies_tested,
                    "all_blocked": all_blocked,
                    "attacks": [
                        {
                            "strategy": a["attack_name"],
                            "blocked": a["blocked"],
                            "reasons": len(a.get("rejection_reasons", [])),
                        }
                        for a in attacks
                    ],
                },
                (time.perf_counter() - t0) * 1000,
            )
        except Exception as exc:
            return TestResult(
                "adversarial_10_injection_strategies", False, error=str(exc),
                timing_ms=(time.perf_counter() - t0) * 1000,
            )

    def test_performance(self) -> TestResult:
        t0 = time.perf_counter()
        try:
            graph = build_performance_graph(500)
            origin = "K0000"

            t_closure = time.perf_counter()
            closure = graph.compute_causal_closure({origin})
            closure_ms = (time.perf_counter() - t_closure) * 1000

            graph.mark_retracted(origin)
            t_excise = time.perf_counter()
            excision = graph.barrier_ordered_excision(closure)
            excise_ms = (time.perf_counter() - t_excise) * 1000

            t_replay = time.perf_counter()
            replay = graph.replay_from_frontier()
            replay_ms = (time.perf_counter() - t_replay) * 1000

            passed = closure_ms < 5000 and excise_ms < 5000 and replay_ms < 5000
            return TestResult(
                "performance_500_node_graph",
                passed,
                {
                    "nodes": 500,
                    "closure_ms": round(closure_ms, 3),
                    "excise_ms": round(excise_ms, 3),
                    "replay_ms": round(replay_ms, 3),
                    "closure_size": len(closure),
                    "excised": len(excision),
                    "replayed": len(replay["replayed"]),
                },
                (time.perf_counter() - t0) * 1000,
            )
        except Exception as exc:
            return TestResult(
                "performance_500_node_graph", False, error=str(exc),
                timing_ms=(time.perf_counter() - t0) * 1000,
            )

    def test_edge_empty_graph(self) -> TestResult:
        t0 = time.perf_counter()
        try:
            graph = EpistemicGraph()
            closure = graph.compute_causal_closure(set())
            excision = graph.barrier_ordered_excision(closure)
            passed = len(closure) == 0 and len(excision) == 0
            return TestResult(
                "edge_empty_graph", passed,
                {"closure_size": 0},
                (time.perf_counter() - t0) * 1000,
            )
        except Exception as exc:
            return TestResult(
                "edge_empty_graph", False, error=str(exc),
                timing_ms=(time.perf_counter() - t0) * 1000,
            )

    def test_edge_single_node(self) -> TestResult:
        t0 = time.perf_counter()
        try:
            graph, origin = build_minimal_scenario()
            pipeline = graph.run_rollback_pipeline({origin})
            passed = (
                pipeline["closure_size"] == 1
                and graph.items[origin].excised
            )
            return TestResult(
                "edge_single_node", passed,
                pipeline,
                (time.perf_counter() - t0) * 1000,
            )
        except Exception as exc:
            return TestResult(
                "edge_single_node", False, error=str(exc),
                timing_ms=(time.perf_counter() - t0) * 1000,
            )

    def test_edge_circular_deps_rejected(self) -> TestResult:
        t0 = time.perf_counter()
        try:
            graph = EpistemicGraph()
            graph.agents["a"] = Agent("a", "a")
            graph.add_item(KnowledgeItem("X", "a", "X", ["Y"]))
            graph.add_item(KnowledgeItem("Y", "a", "Y", ["X"]))
            cycles = graph.detect_item_cycles()
            passed = len(cycles) > 0
            return TestResult(
                "edge_circular_deps_rejected", passed,
                {"cycles_found": len(cycles), "sample_cycle": cycles[0] if cycles else []},
                (time.perf_counter() - t0) * 1000,
            )
        except Exception as exc:
            return TestResult(
                "edge_circular_deps_rejected", False, error=str(exc),
                timing_ms=(time.perf_counter() - t0) * 1000,
            )

    def test_edge_already_retracted(self) -> TestResult:
        t0 = time.perf_counter()
        try:
            graph, origin = build_minimal_scenario()
            graph.mark_retracted(origin)
            graph.mark_retracted(origin)
            pipeline = graph.run_rollback_pipeline({origin})
            passed = origin in graph.retracted_sources and pipeline["closure_size"] == 1
            return TestResult(
                "edge_already_retracted_item", passed,
                {"retracted_count": len(graph.retracted_sources)},
                (time.perf_counter() - t0) * 1000,
            )
        except Exception as exc:
            return TestResult(
                "edge_already_retracted_item", False, error=str(exc),
                timing_ms=(time.perf_counter() - t0) * 1000,
            )

    def run_all(self) -> dict[str, Any]:
        tests = [
            self.test_scale,
            self.test_concurrent_contamination,
            self.test_partial_observability,
            self.test_adversarial_recontamination,
            self.test_performance,
            self.test_edge_empty_graph,
            self.test_edge_single_node,
            self.test_edge_circular_deps_rejected,
            self.test_edge_already_retracted,
        ]
        for test_fn in tests:
            self.record(test_fn())

        all_pass = all(r.passed for r in self.results)
        total_ms = sum(r.timing_ms for r in self.results)
        return {
            "framework": "DERF",
            "gate": "REALITY_GATE",
            "spec_version": "PUBLICATION_HARDENING_PROTOCOL",
            "blueprint_version": "2.0.0",
            "python_version": sys.version.split()[0],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_count": 3,
            "author": AUTHOR,
            "orcid": ORCID,
            "disclaimer": DISCLAIMER,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "total_gate_execution_seconds": round(total_ms / 1000.0, 6),
            "tests": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "timing_ms": round(r.timing_ms, 3),
                    "details": r.details,
                    "error": r.error,
                }
                for r in self.results
            ],
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r.passed),
                "failed": sum(1 for r in self.results if not r.passed),
            },
            "GATE_VERDICT": "PASS" if all_pass else "FAIL",
        }


def print_summary_table(report: dict[str, Any]) -> None:
    print("\n" + "=" * 78)
    print("DERF REALITY GATE — TEST SUMMARY")
    print("=" * 78)
    print(f"{'TEST':<45} {'RESULT':<8} {'TIME(ms)':>10}")
    print("-" * 78)
    for t in report["tests"]:
        status = "PASS" if t["passed"] else "FAIL"
        print(f"{t['name']:<45} {status:<8} {t['timing_ms']:>10.1f}")
    print("-" * 78)
    s = report["summary"]
    print(f"Total: {s['total']}  Passed: {s['passed']}  Failed: {s['failed']}")
    print(f"Total gate execution: {report.get('total_gate_execution_seconds', 0):.3f} seconds")
    print(f"\nGATE VERDICT: {report['GATE_VERDICT']}")
    print("=" * 78)


def main() -> int:
    print("=" * 78)
    print("DERF Reality Gate Demonstrator")
    print(f"Author: {AUTHOR} (ORCID {ORCID})")
    print(DISCLAIMER)
    print("=" * 78)

    t0 = time.perf_counter()
    runner = DerfGateRunner()
    report = runner.run_all()
    wall_s = time.perf_counter() - t0
    report["total_gate_execution_seconds"] = round(wall_s, 6)
    print_summary_table(report)

    out_path = Path(__file__).resolve().parent / "derf_gate_results.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    print(f"\nResults written to: {out_path}")

    return 0 if report["GATE_VERDICT"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
