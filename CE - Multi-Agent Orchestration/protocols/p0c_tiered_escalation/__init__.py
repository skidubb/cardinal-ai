"""P0c: Tiered Escalation — Cascading protocols on failure."""

from .orchestrator import TieredEscalation, TierResult, EscalationResult

__all__ = ["TieredEscalation", "TierResult", "EscalationResult"]
