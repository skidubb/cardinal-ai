"""Unified model pricing for the CE-AGENTS monorepo.

Single source of truth for all model pricing across Agent Builder,
Multi-Agent Orchestration, and CE-Evals. Verified against provider
documentation.

Pricing is per million tokens (MTok) in USD: (input, output).
"""

from __future__ import annotations

from enum import StrEnum

# ---------------------------------------------------------------------------
# Verification date
# ---------------------------------------------------------------------------

PRICING_VERIFIED_DATE = "2026-03-09"
"""Date pricing was last verified against provider documentation."""

# ---------------------------------------------------------------------------
# Model tiers
# ---------------------------------------------------------------------------


class ModelTier(StrEnum):
    """Canonical Anthropic model tiers."""

    OPUS = "claude-opus-4-6"
    SONNET = "claude-sonnet-4-6"
    HAIKU = "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# Multiplier constants
# ---------------------------------------------------------------------------

CACHE_READ_MULTIPLIER: float = 0.10
"""Cached input tokens are charged at 10% of normal input rate."""

CACHE_WRITE_MULTIPLIER: float = 1.25
"""Cache write tokens are charged at 125% of normal input rate."""

BATCH_DISCOUNT: float = 0.50
"""Batch API discount: 50% off both input and output costs."""

# ---------------------------------------------------------------------------
# Model pricing: (input_per_mtok, output_per_mtok)
# ---------------------------------------------------------------------------

MODEL_PRICING: dict[str, tuple[float, float]] = {
    # Anthropic — current generation (verified 2026-03-09)
    "claude-opus-4-6": (5.00, 25.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    # Anthropic — aliases
    "claude-haiku-4-5": (1.00, 5.00),
    # Anthropic — previous generation
    "claude-opus-4-5-20251101": (5.00, 25.00),
    "claude-opus-4-5": (5.00, 25.00),
    "claude-opus-4-1-20250805": (15.00, 75.00),
    "claude-opus-4-1": (15.00, 75.00),
    "claude-sonnet-4-5-20250929": (3.00, 15.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-sonnet-4-20250514": (3.00, 15.00),
    "claude-sonnet-4-0": (3.00, 15.00),
    "claude-opus-4-20250514": (15.00, 75.00),
    "claude-opus-4-0": (15.00, 75.00),
    # OpenAI (from CE-Evals, approximate Feb 2026)
    "gpt-5.2": (2.50, 10.00),
    "gpt-4o": (2.50, 10.00),
    "o3-mini": (1.10, 4.40),
    # Google (from CE-Evals, approximate Feb 2026)
    "gemini-3.1-pro-preview": (1.25, 5.00),
    "gemini-2.5-pro": (1.25, 5.00),
    "gemini-2.0-flash": (0.10, 0.40),
}

# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

# Substring fallback order for models not found by exact match
_SUBSTRING_FALLBACKS: list[tuple[str, tuple[float, float]]] = [
    ("opus-4-6", (5.00, 25.00)),
    ("opus-4-5", (5.00, 25.00)),
    ("opus-4-1", (15.00, 75.00)),
    ("opus-4-0", (15.00, 75.00)),
    ("opus", (5.00, 25.00)),  # default opus = current gen
    ("sonnet", (3.00, 15.00)),
    ("haiku", (1.00, 5.00)),
    ("gpt", (2.50, 10.00)),
    ("gemini", (1.25, 5.00)),
]

# Default pricing for completely unknown models (conservative = current Opus)
_DEFAULT_PRICING: tuple[float, float] = (5.00, 25.00)


def get_pricing(model: str) -> tuple[float, float]:
    """Return (input_per_mtok, output_per_mtok) for a model string.

    Lookup order:
    1. Exact match in MODEL_PRICING
    2. Substring fallback (opus/sonnet/haiku/gpt/gemini)
    3. Default to current Opus-tier pricing (most conservative)
    """
    # Exact match
    if model in MODEL_PRICING:
        return MODEL_PRICING[model]

    # Substring fallback
    lower = model.lower()
    for substring, pricing in _SUBSTRING_FALLBACKS:
        if substring in lower:
            return pricing

    # Conservative default
    return _DEFAULT_PRICING


def cost_for_model(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
    batch: bool = False,
) -> float:
    """Calculate total USD cost for an API call.

    Args:
        model: Model ID string (exact or partial).
        input_tokens: Number of input tokens (excluding cache tokens).
        output_tokens: Number of output tokens.
        cache_read_tokens: Tokens read from prompt cache (charged at
            CACHE_READ_MULTIPLIER of normal input rate).
        cache_write_tokens: Tokens written to prompt cache (charged at
            CACHE_WRITE_MULTIPLIER of normal input rate).
        batch: Whether batch API pricing applies (BATCH_DISCOUNT off total).

    Returns:
        Total cost in USD.
    """
    input_rate, output_rate = get_pricing(model)

    # Per-token rates
    input_per_token = input_rate / 1_000_000
    output_per_token = output_rate / 1_000_000

    # Input cost: regular tokens at full rate
    cost = input_tokens * input_per_token

    # Cache read tokens at reduced rate
    cost += cache_read_tokens * input_per_token * CACHE_READ_MULTIPLIER

    # Cache write tokens at elevated rate
    cost += cache_write_tokens * input_per_token * CACHE_WRITE_MULTIPLIER

    # Output cost
    cost += output_tokens * output_per_token

    # Batch discount
    if batch:
        cost *= (1 - BATCH_DISCOUNT)

    return cost
