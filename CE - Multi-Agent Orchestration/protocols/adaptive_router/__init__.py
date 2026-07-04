"""Adaptive Router — classify a question, pick a protocol, execute it.

Thin shim that wires P0a (classifier) to the existing api/runner (executor)
via a resolver that reads capability.yaml files for safety rails.
"""

from .orchestrator import (
    AdaptiveRouterOrchestrator,
    RouterDecision,
    ConfidenceGateError,
)
from .resolver import (
    Resolver,
    ResolveResult,
    ResolveError,
)

__all__ = [
    "AdaptiveRouterOrchestrator",
    "RouterDecision",
    "ConfidenceGateError",
    "Resolver",
    "ResolveResult",
    "ResolveError",
]
