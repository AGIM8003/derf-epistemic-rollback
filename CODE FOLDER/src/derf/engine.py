"""DERFEngine — usable research library API. Author: Haxhijaha, Agim ORCID 0009-0002-3234-7765."""
from __future__ import annotations

import time
from typing import Any

from .core import Agent, EpistemicGraph, KnowledgeItem
from .types import ExcisionResult
from .validators import detect_cycles, validate_item_id, validate_sources


class DERFEngine:
    """Epistemic rollback engine: causal closure, excision, replay, recontamination checks.

    Usage:
        engine = DERFEngine()
        engine.add_knowledge("K1", sources=[])
        engine.add_knowledge("K2", depends_on=["K1"])
        engine.mark_contaminated("K1", reason="retracted")
        result = engine.excise()
    """

    def __init__(self, default_agent_id: str = "user_agent") -> None:
        self._graph = EpistemicGraph()
        self._default_agent = default_agent_id
        self._reasons: dict[str, str] = {}
        if default_agent_id not in self._graph.agents:
            self._graph.add_agent(Agent(default_agent_id, "library_user", depends_on=[]))

    def add_knowledge(
        self,
        item_id: str,
        *,
        sources: list[str] | None = None,
        depends_on: list[str] | None = None,
        claim: str = "",
        agent_id: str | None = None,
    ) -> None:
        """Register a knowledge item. `depends_on` is an alias for `sources`."""
        item_id = validate_item_id(item_id)
        if item_id in self._graph.items:
            raise ValueError(f"duplicate knowledge item: {item_id}")
        deps = validate_sources(depends_on if depends_on is not None else sources)
        aid = agent_id or self._default_agent
        if aid not in self._graph.agents:
            self._graph.add_agent(Agent(aid, "library_user", depends_on=[]))
        # cycle check on prospective graph
        provisional = {iid: list(it.source_ids) for iid, it in self._graph.items.items()}
        provisional[item_id] = deps
        detect_cycles(provisional)
        item = KnowledgeItem(
            item_id=item_id,
            agent_id=aid,
            claim=claim or item_id,
            source_ids=deps,
            derived=bool(deps),
        )
        self._graph.items[item_id] = item
        self._graph.agents[aid].knowledge[item_id] = item

    def add_dependency(self, item_id: str, depends_on: list[str]) -> None:
        """Add dependency edges to an existing item."""
        item_id = validate_item_id(item_id)
        if item_id not in self._graph.items:
            raise ValueError(f"unknown item: {item_id}")
        deps = validate_sources(depends_on)
        provisional = {iid: list(it.source_ids) for iid, it in self._graph.items.items()}
        provisional[item_id] = list(dict.fromkeys(provisional[item_id] + deps))
        detect_cycles(provisional)
        self._graph.items[item_id].source_ids = provisional[item_id]

    def mark_contaminated(self, item_id: str, reason: str = "") -> None:
        """Mark an item as a contamination/retraction origin."""
        item_id = validate_item_id(item_id)
        if item_id not in self._graph.items:
            raise ValueError(f"unknown item: {item_id}")
        self._graph.mark_retracted(item_id)
        self._reasons[item_id] = reason or "unspecified"

    def causal_closure(self, origins: set[str] | None = None) -> set[str]:
        """Compute causal closure of contaminated origins (or all retracted)."""
        origins = set(origins) if origins is not None else set(self._graph.retracted_sources)
        if not origins:
            return set()
        unknown = origins - set(self._graph.items)
        if unknown:
            raise ValueError(f"unknown origin ids: {sorted(unknown)}")
        return self._graph.compute_causal_closure(origins)

    def excise(self, *, attempt_recontamination_path: list[str] | None = None) -> ExcisionResult:
        """Run closure → barrier excision → frontier replay → optional reinjection check."""
        t0 = time.perf_counter()
        origins = set(self._graph.retracted_sources)
        if not origins and not self._graph.items:
            elapsed = time.perf_counter() - t0
            return ExcisionResult([], [], [], True, True, elapsed)
        if not origins:
            raise ValueError("no contaminated items marked; call mark_contaminated() first")
        closure = self._graph.compute_causal_closure(origins)
        excised = self._graph.barrier_ordered_excision(closure)
        replay = self._graph.replay_from_frontier()
        blocked = True
        if attempt_recontamination_path is not None and origins:
            origin = sorted(origins)[0]
            blocked = bool(
                self._graph.attempt_recontamination(origin, attempt_recontamination_path)["blocked"]
            )
        clean = sorted(self._graph.clean_frontier())
        elapsed = time.perf_counter() - t0
        return ExcisionResult(
            contaminated_items=sorted(origins),
            excised_items=list(excised),
            clean_items=clean,
            replay_success=True,
            recontamination_blocked=blocked,
            execution_time_seconds=round(elapsed, 6),
            closure_size=len(closure),
            replay_details=replay,
            contamination_reasons=dict(self._reasons),
        )

    def check_recontamination(self, retracted_id: str, alternate_path: list[str]) -> dict[str, Any]:
        """Attempt reinjection via alternate path; returns rejection proof."""
        retracted_id = validate_item_id(retracted_id)
        path = validate_sources(alternate_path)
        return self._graph.attempt_recontamination(retracted_id, path)

    @property
    def graph(self) -> EpistemicGraph:
        """Access underlying EpistemicGraph (advanced / research use)."""
        return self._graph
