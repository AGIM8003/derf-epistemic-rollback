"""DERF core graph primitives (architecture-frozen). Author: Haxhijaha, Agim ORCID 0009-0002-3234-7765."""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class KnowledgeItem:
    """A single epistemic claim held by an agent."""

    item_id: str
    agent_id: str
    claim: str
    source_ids: list[str]  # provenance: upstream knowledge item IDs
    derived: bool = False
    contaminated: bool = False
    excised: bool = False
    retracted: bool = False

    def provenance_chain(self, registry: dict[str, KnowledgeItem]) -> list[str]:
        """Return ordered provenance chain (depth-first, deduplicated)."""
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


@dataclass
class Agent:
    """An epistemic agent in the dependency DAG."""

    agent_id: str
    role: str
    depends_on: list[str] = field(default_factory=list)  # upstream agent IDs
    knowledge: dict[str, KnowledgeItem] = field(default_factory=dict)


@dataclass
class EpistemicGraph:
    """DAG of agents and their knowledge items."""

    agents: dict[str, Agent] = field(default_factory=dict)
    items: dict[str, KnowledgeItem] = field(default_factory=dict)
    retracted_sources: set[str] = field(default_factory=set)

    def add_agent(self, agent: Agent) -> None:
        self.agents[agent.agent_id] = agent
        for item in agent.knowledge.values():
            self.items[item.item_id] = item

    def mark_retracted(self, item_id: str) -> None:
        """Mark a source knowledge item as retracted (contamination origin)."""
        self.retracted_sources.add(item_id)
        if item_id in self.items:
            self.items[item_id].retracted = True
            self.items[item_id].contaminated = True

    def agent_topo_order(self) -> list[str]:
        """Return agents in topological order (dependencies first)."""
        in_degree: dict[str, int] = {aid: 0 for aid in self.agents}
        for agent in self.agents.values():
            for dep in agent.depends_on:
                if dep in self.agents:
                    in_degree[agent.agent_id] += 1

        # Rebuild: in_degree counts how many deps each agent has
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

    def item_dependency_graph(self) -> dict[str, list[str]]:
        """Map each item to items that depend on it (reverse edges)."""
        dependents: dict[str, list[str]] = defaultdict(list)
        for item in self.items.values():
            for src in item.source_ids:
                dependents[src].append(item.item_id)
        return dict(dependents)

    def compute_causal_closure(self, origin_ids: set[str]) -> set[str]:
        """
        Compute causal closure: all items transitively depending on
        contaminated origins.
        """
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

    def barrier_ordered_excision(self, closure: set[str]) -> list[str]:
        """
        Remove contaminated items in barrier order: excise only when all
        downstream dependents in the closure have already been excised
        (reverse topological order within closure).
        """
        dependents = self.item_dependency_graph()
        closure_set = set(closure)
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

        while queue:
            current = queue.popleft()
            if current not in closure_set:
                continue
            item = self.items[current]
            if not item.excised:
                item.excised = True
                item.contaminated = True
                excision_order.append(current)

            for src_id, item_obj in self.items.items():
                if current in item_obj.source_ids and src_id in closure_set:
                    in_closure_dependents[src_id] -= 1
                    if in_closure_dependents[src_id] == 0:
                        queue.append(src_id)

        # Process remaining closure items not yet excised (sources first)
        remaining = [iid for iid in closure_set if not self.items[iid].excised]
        for iid in sorted(remaining, key=lambda x: len(self.items[x].source_ids)):
            if not self.items[iid].excised:
                self.items[iid].excised = True
                self.items[iid].contaminated = True
                excision_order.append(iid)

        return excision_order

    def clean_frontier(self) -> set[str]:
        """Items not excised and not depending on excised sources."""
        frontier: set[str] = set()
        for item in self.items.values():
            if item.excised:
                continue
            sources_excised = any(
                self.items[s].excised for s in item.source_ids if s in self.items
            )
            if not sources_excised:
                frontier.add(item.item_id)
        return frontier

    def replay_from_frontier(self) -> dict[str, Any]:
        """
        Re-derive knowledge from uncontaminated sources on the clean frontier.
        Returns replay results.
        """
        frontier = self.clean_frontier()
        replayed: list[dict[str, str]] = []
        still_missing: list[str] = []

        excised_items = [item for item in self.items.values() if item.excised]
        for item in excised_items:
            # Re-derive from any surviving uncontaminated sources
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
                )
                self.items[new_item.item_id] = new_item
                agent = self.agents[item.agent_id]
                agent.knowledge[new_item.item_id] = new_item
                replayed.append({
                    "original": item.item_id,
                    "replayed_as": new_item.item_id,
                    "claim": new_item.claim,
                    "partial": partial,
                    "clean_sources": clean_sources,
                    "lost_sources": excised_sources,
                })
            else:
                still_missing.append(item.item_id)

        return {
            "frontier_size": len(frontier),
            "frontier_items": sorted(frontier),
            "replayed": replayed,
            "unrecoverable": still_missing,
        }

    def attempt_recontamination(
        self, retracted_id: str, alternate_path: list[str]
    ) -> dict[str, Any]:
        """
        Try to re-inject retracted knowledge via an alternate provenance path.
        Returns rejection proof if blocked.
        """
        retracted = self.items.get(retracted_id)
        if retracted is None:
            return {"blocked": True, "reason": "retracted item not found"}

        # Build a new item claiming alternate provenance but same claim
        fake_id = f"reinject_{retracted_id}"
        fake_item = KnowledgeItem(
            item_id=fake_id,
            agent_id="agent_reinjector",
            claim=retracted.claim,
            source_ids=alternate_path,
            derived=True,
        )

        # Rejection rules
        rejection_reasons: list[str] = []

        if retracted_id in self.retracted_sources:
            rejection_reasons.append(
                f"Source {retracted_id} is on retracted-source registry"
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

        # Check if alternate path secretly resolves to same retracted origin
        for src in alternate_path:
            if src == retracted_id:
                rejection_reasons.append(
                    "Alternate path is the retracted item itself"
                )
            item = self.items.get(src)
            if item and retracted_id in item.provenance_chain(self.items):
                rejection_reasons.append(
                    f"Alternate path {src} transitively depends on {retracted_id}"
                )

        blocked = len(rejection_reasons) > 0

        if not blocked:
            self.items[fake_id] = fake_item

        return {
            "attempted_item": fake_id,
            "claim": fake_item.claim,
            "alternate_path": alternate_path,
            "blocked": blocked,
            "rejection_reasons": rejection_reasons,
            "reinjector_accepted": not blocked,
        }

    def snapshot(self) -> dict[str, Any]:
        """Serialisable state snapshot."""
        return {
            "agents": {
                aid: {
                    "role": a.role,
                    "depends_on": a.depends_on,
                    "knowledge_count": len(a.knowledge),
                }
                for aid, a in self.agents.items()
            },
            "items": {
                iid: {
                    "agent_id": it.agent_id,
                    "claim": it.claim,
                    "source_ids": it.source_ids,
                    "derived": it.derived,
                    "contaminated": it.contaminated,
                    "excised": it.excised,
                    "retracted": it.retracted,
                }
                for iid, it in self.items.items()
            },
            "retracted_sources": sorted(self.retracted_sources),
        }

