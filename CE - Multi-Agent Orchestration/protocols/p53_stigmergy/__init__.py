"""P53 Stigmergic Coordination — decentralized trace-field protocol.

Pure helpers (parse/decay/harvest/format + dataclasses) are eagerly exported
from `.field` since they have no LLM dependencies. The orchestrator is
imported lazily so importing this package in slim environments (no litellm,
no anthropic) doesn't fail.
"""

from .field import (
    DECAY_PER_WAVE,
    DEFAULT_TOP_N_PER_TYPE,
    DEFAULT_WAVES,
    LocationSummary,
    StigmergyResult,
    TRACE_TYPES,
    Trace,
    format_trace_field,
    harvest_field,
    parse_traces,
)


def __getattr__(name: str):
    # Lazy-load the orchestrator so unit tests can import `field` without
    # pulling in litellm/anthropic.
    if name in ("StigmergyOrchestrator",):
        from .orchestrator import StigmergyOrchestrator

        return StigmergyOrchestrator
    raise AttributeError(f"module 'protocols.p53_stigmergy' has no attribute {name!r}")


__all__ = [
    "StigmergyOrchestrator",
    "StigmergyResult",
    "Trace",
    "LocationSummary",
    "DECAY_PER_WAVE",
    "DEFAULT_WAVES",
    "DEFAULT_TOP_N_PER_TYPE",
    "TRACE_TYPES",
    "parse_traces",
    "format_trace_field",
    "harvest_field",
]
