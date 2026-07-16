"""DERF public result types. Author: Haxhijaha, Agim ORCID 0009-0002-3234-7765."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Re-export core item type for API users
from .core import KnowledgeItem, Agent, EpistemicGraph


@dataclass
class ExcisionResult:
    """Structured result of a DERF excision pipeline run."""

    contaminated_items: list[str]
    excised_items: list[str]
    clean_items: list[str]
    replay_success: bool
    recontamination_blocked: bool
    execution_time_seconds: float
    closure_size: int = 0
    replay_details: dict[str, Any] = field(default_factory=dict)
    contamination_reasons: dict[str, str] = field(default_factory=dict)
