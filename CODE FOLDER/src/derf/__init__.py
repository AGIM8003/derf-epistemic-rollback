"""DERF — Decentralized Epistemic Rollback Fabric (research library)."""
from .core import Agent, EpistemicGraph, KnowledgeItem
from .engine import DERFEngine
from .types import ExcisionResult

__all__ = [
    "DERFEngine",
    "ExcisionResult",
    "KnowledgeItem",
    "Agent",
    "EpistemicGraph",
]
__version__ = "2.3.0"
