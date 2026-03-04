"""Lightweight per-protocol cost tracker for the coordination layer.

Usage:
    from protocols.cost_tracker import ProtocolCostTracker
    from protocols.llm import set_cost_tracker

    tracker = ProtocolCostTracker()
    set_cost_tracker(tracker)

    # ... run protocol ...

    print(tracker.summary())
    set_cost_tracker(None)  # clear when done
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Pricing constants  (Anthropic public pricing, March 2026)
# Per million tokens (MTok) — input / output in USD
# ---------------------------------------------------------------------------

_PRICING: dict[str, dict[str, float]] = {
    # Exact model IDs
    "claude-opus-4-6":            {"input": 15.00, "output": 75.00},
    "claude-opus-4-5":            {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-6":          {"input":  3.00, "output": 15.00},
    "claude-sonnet-4-5-20250929": {"input":  3.00, "output": 15.00},
    "claude-haiku-4-5-20251001":  {"input":  0.80, "output":  4.00},
    "claude-haiku-4-5":           {"input":  0.80, "output":  4.00},
    # Substring fallbacks (matched in order)
    "opus":   {"input": 15.00, "output": 75.00},
    "sonnet": {"input":  3.00, "output": 15.00},
    "haiku":  {"input":  0.80, "output":  4.00},
}

_CACHE_READ_MULTIPLIER = 0.10  # cached input tokens charged at 10% of normal rate


def _price_for_model(model: str) -> dict[str, float]:
    """Return input/output pricing for a model string."""
    if model in _PRICING:
        return _PRICING[model]
    lower = model.lower()
    for key in ("opus", "sonnet", "haiku"):
        if key in lower:
            return _PRICING[key]
    # Conservative fallback — charge at Opus rate
    return _PRICING["opus"]


def _compute_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
) -> float:
    """Return USD cost for a single API call."""
    pricing = _price_for_model(model)
    input_rate = pricing["input"] / 1_000_000
    output_rate = pricing["output"] / 1_000_000

    non_cached = max(0, input_tokens - cached_tokens)
    input_cost = non_cached * input_rate + cached_tokens * input_rate * _CACHE_READ_MULTIPLIER
    output_cost = output_tokens * output_rate
    return input_cost + output_cost


# ---------------------------------------------------------------------------
# Per-model accumulator
# ---------------------------------------------------------------------------

@dataclass
class _ModelStats:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    cost_usd: float = 0.0


# ---------------------------------------------------------------------------
# ProtocolCostTracker
# ---------------------------------------------------------------------------

class ProtocolCostTracker:
    """Accumulate token usage and compute USD cost for a single protocol run.

    Thread-safety note: protocols use asyncio (single thread), so no locking needed.
    """

    def __init__(self) -> None:
        self._calls: int = 0
        self._total_cost: float = 0.0
        self._by_model: dict[str, _ModelStats] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def track(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
    ) -> None:
        """Record one API call's token usage and accumulate cost."""
        cost = _compute_cost(model, input_tokens, output_tokens, cached_tokens)
        self._calls += 1
        self._total_cost += cost

        stats = self._by_model.setdefault(model, _ModelStats())
        stats.calls += 1
        stats.input_tokens += input_tokens
        stats.output_tokens += output_tokens
        stats.cached_tokens += cached_tokens
        stats.cost_usd += cost

    @property
    def total_cost(self) -> float:
        """Total USD cost accumulated so far."""
        return self._total_cost

    def summary(self) -> dict[str, Any]:
        """Return a cost summary dict.

        Shape::

            {
                "total_usd": float,
                "calls": int,
                "by_model": {
                    "<model>": {
                        "calls": int,
                        "input_tokens": int,
                        "output_tokens": int,
                        "cached_tokens": int,
                        "cost_usd": float,
                    },
                    ...
                }
            }
        """
        return {
            "total_usd": round(self._total_cost, 6),
            "calls": self._calls,
            "by_model": {
                model: {
                    "calls": s.calls,
                    "input_tokens": s.input_tokens,
                    "output_tokens": s.output_tokens,
                    "cached_tokens": s.cached_tokens,
                    "cost_usd": round(s.cost_usd, 6),
                }
                for model, s in self._by_model.items()
            },
        }

    def reset(self) -> None:
        """Clear all accumulated data."""
        self._calls = 0
        self._total_cost = 0.0
        self._by_model.clear()
