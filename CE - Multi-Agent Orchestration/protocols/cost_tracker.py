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

import logging
import os
from dataclasses import dataclass, field
from typing import Any

from ce_shared.pricing import cost_for_model, get_pricing

logger = logging.getLogger(__name__)


def _compute_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
) -> float:
    """Return USD cost for a single API call.

    Thin wrapper around ``ce_shared.pricing.cost_for_model``.

    Note: *input_tokens* here is the **total** input count (including any
    cached portion).  ``cost_for_model`` expects regular (non-cached) tokens
    separately, so we subtract *cached_tokens* before delegating.
    """
    non_cached = max(0, input_tokens - cached_tokens)
    return cost_for_model(
        model,
        input_tokens=non_cached,
        output_tokens=output_tokens,
        cache_read_tokens=cached_tokens,
    )


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
# Per-agent accumulator
# ---------------------------------------------------------------------------

@dataclass
class _AgentStats:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    cost_usd: float = 0.0
    by_model: dict[str, _ModelStats] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# ProtocolCostTracker
# ---------------------------------------------------------------------------

class ProtocolCostTracker:
    """Accumulate token usage and compute USD cost for a single protocol run.

    Thread-safety note: protocols use asyncio (single thread), so no locking needed.
    """

    def __init__(self, cost_ceiling_usd: float | None = None) -> None:
        self._calls: int = 0
        self._total_cost: float = 0.0
        self._by_model: dict[str, _ModelStats] = {}
        self._by_agent: dict[str, _AgentStats] = {}

        # Budget ceiling: warn (but don't halt) when exceeded
        if cost_ceiling_usd is not None:
            self.cost_ceiling_usd: float | None = cost_ceiling_usd
        else:
            env_val = os.environ.get("PROTOCOL_COST_CEILING")
            self.cost_ceiling_usd = float(env_val) if env_val else None
        self._ceiling_warned: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def track(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        agent_name: str | None = None,
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

        if agent_name:
            agent_key = agent_name.strip().lower().replace("_", "-").replace(" ", "-")
            agent_stats = self._by_agent.setdefault(agent_key, _AgentStats())
            agent_stats.calls += 1
            agent_stats.input_tokens += input_tokens
            agent_stats.output_tokens += output_tokens
            agent_stats.cached_tokens += cached_tokens
            agent_stats.cost_usd += cost
            model_stats = agent_stats.by_model.setdefault(model, _ModelStats())
            model_stats.calls += 1
            model_stats.input_tokens += input_tokens
            model_stats.output_tokens += output_tokens
            model_stats.cached_tokens += cached_tokens
            model_stats.cost_usd += cost

        # Budget ceiling check (warn once per run)
        if (
            self.cost_ceiling_usd is not None
            and not self._ceiling_warned
            and self._total_cost > self.cost_ceiling_usd
        ):
            self._ceiling_warned = True
            logger.warning(
                "Protocol cost $%.4f exceeds ceiling $%.2f%s",
                self._total_cost,
                self.cost_ceiling_usd,
                f" (model: {model})" if model else "",
            )

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
            "by_agent": {
                agent: {
                    "calls": s.calls,
                    "input_tokens": s.input_tokens,
                    "output_tokens": s.output_tokens,
                    "cached_tokens": s.cached_tokens,
                    "cost_usd": round(s.cost_usd, 6),
                    "primary_model": max(
                        s.by_model.items(),
                        key=lambda kv: kv[1].calls,
                    )[0] if s.by_model else "",
                    "by_model": {
                        model: {
                            "calls": ms.calls,
                            "input_tokens": ms.input_tokens,
                            "output_tokens": ms.output_tokens,
                            "cached_tokens": ms.cached_tokens,
                            "cost_usd": round(ms.cost_usd, 6),
                        }
                        for model, ms in s.by_model.items()
                    },
                }
                for agent, s in self._by_agent.items()
            },
        }

    def reset(self) -> None:
        """Clear all accumulated data."""
        self._calls = 0
        self._total_cost = 0.0
        self._by_model.clear()
        self._by_agent.clear()
