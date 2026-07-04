"""Token cost estimation — delegates to ce-shared as single source of truth."""

from __future__ import annotations

from ce_shared.pricing import MODEL_PRICING as PRICING  # re-export for compat
from ce_shared.pricing import cost_for_model


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str = "claude-opus-4-7",
) -> float:
    """Estimate cost in USD."""
    return cost_for_model(model, input_tokens, output_tokens)
