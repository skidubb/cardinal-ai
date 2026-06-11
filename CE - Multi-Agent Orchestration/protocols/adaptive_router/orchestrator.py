"""Adaptive Router Orchestrator — classify + resolve + (optionally) execute.

The orchestrator itself only decides. Execution is the caller's job (CLI or API
runner). This keeps the router composable: it can be used from a chain, a
notebook, or a future scheduler without coupling to the FastAPI runner.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any

from protocols.p0a_reasoning_router.orchestrator import ReasoningRouter, RouterResult

from .resolver import Resolver, ResolveResult


# Confidence thresholds — tunable via constructor
DEFAULT_HIGH = 80
DEFAULT_MID = 50

# ---------------------------------------------------------------------------
# In-process router decision cache
# ---------------------------------------------------------------------------

_ROUTER_CACHE_TTL = 15 * 60  # 15 minutes in seconds
_ROUTER_CACHE_MAX = 256  # max entries; evict oldest on overflow

# {cache_key: (RouterDecision, inserted_at_monotonic)}
_router_cache: dict[str, tuple["RouterDecision", float]] = {}


def _router_cache_key(question: str, agents: list[str] | None, mode: str) -> str:
    """Stable SHA-256 key for a router decide() call."""
    payload = json.dumps(
        {
            "q": question.strip().lower(),
            "agents": sorted(agents) if agents else [],
            "mode": mode,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _router_cache_get(key: str) -> "RouterDecision | None":
    """Return a cached decision if it exists and hasn't expired."""
    entry = _router_cache.get(key)
    if entry is None:
        return None
    decision, inserted_at = entry
    if time.monotonic() - inserted_at > _ROUTER_CACHE_TTL:
        del _router_cache[key]
        return None
    return decision


def _router_cache_put(key: str, decision: "RouterDecision") -> None:
    """Store a decision, evicting the oldest entry when the cache is full."""
    global _router_cache
    if len(_router_cache) >= _ROUTER_CACHE_MAX:
        # Evict the entry with the smallest insertion timestamp
        oldest_key = min(_router_cache, key=lambda k: _router_cache[k][1])
        del _router_cache[oldest_key]
    _router_cache[key] = (decision, time.monotonic())


class ConfidenceGateError(Exception):
    """Raised when confidence is too low to auto-execute."""

    def __init__(self, message: str, decision: "RouterDecision") -> None:
        super().__init__(message)
        self.decision = decision


@dataclass
class RouterDecision:
    """Unified decision: classifier output + resolved execution plan."""

    question: str
    problem_type: str
    confidence: int
    tier: str  # "high" | "mid" | "low"
    auto_executable: bool
    reasoning: str
    plan: ResolveResult | None
    raw_router: dict[str, Any]
    adjustments: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "problem_type": self.problem_type,
            "confidence": self.confidence,
            "tier": self.tier,
            "auto_executable": self.auto_executable,
            "reasoning": self.reasoning,
            "adjustments": self.adjustments,
            "plan": (
                {
                    "protocol_key": self.plan.protocol_key,
                    "protocol_id": self.plan.protocol_id,
                    "name": self.plan.name,
                    "cost_tier": self.plan.cost_tier,
                    "agent_keys": self.plan.agent_keys,
                    "supports_rounds": self.plan.supports_rounds,
                }
                if self.plan
                else None
            ),
            "raw_router": self.raw_router,
        }


class AdaptiveRouterOrchestrator:
    """Classify a question, resolve to an executable plan, return a decision.

    This class does NOT execute the chosen protocol. The CLI and API layer
    consume `RouterDecision.plan` and call their own executor (existing
    runner.run_protocol_stream or direct protocol invocation).
    """

    def __init__(
        self,
        *,
        resolver: Resolver | None = None,
        classifier: ReasoningRouter | None = None,
        high_threshold: int = DEFAULT_HIGH,
        mid_threshold: int = DEFAULT_MID,
    ) -> None:
        self.resolver = resolver or Resolver()
        self.classifier = classifier or ReasoningRouter()
        self.high_threshold = high_threshold
        self.mid_threshold = mid_threshold

    async def decide(
        self,
        question: str,
        *,
        requested_agents: list[str] | None = None,
        mode: str = "default",
    ) -> RouterDecision:
        """Classify the question and return a decision.

        Results are memoized in-process for ``_ROUTER_CACHE_TTL`` (15 min) keyed
        by sha256(question + sorted agents + mode).  Cache hits skip the LLM
        classifier call entirely — useful when the UI polls decide() before
        committing to a full run.

        Does not raise on low confidence — returns a decision with
        auto_executable=False. Callers choose whether to prompt the user
        or abort.
        """
        cache_key = _router_cache_key(question, requested_agents, mode)
        cached = _router_cache_get(cache_key)
        if cached is not None:
            return cached

        classifier_result: RouterResult = await self.classifier.run(question)

        tier = self._tier(classifier_result.problem_type_confidence)
        alt_pairs = [(a.protocol, a.name) for a in classifier_result.alternatives]

        plan: ResolveResult | None = None
        adjustments: list[str] = []
        try:
            plan = self.resolver.resolve(
                recommended_protocol_id=classifier_result.recommended_protocol,
                alternatives=alt_pairs,
                requested_agents=requested_agents,
            )
            adjustments = plan.adjustments
        except Exception as exc:
            adjustments = [f"resolver failed: {exc}"]

        # For low-tier short-circuits (P00 Direct / P01 Single Agent), the
        # cost/risk of a wrong route is negligible — user can easily re-run
        # with a better-matched protocol. Allow auto-execute at "mid" tier for
        # these only. Multi-agent protocols still require "high" confidence.
        low_tier_short_circuit = (
            plan is not None
            and plan.protocol_key in {"p00_direct", "p01_single_agent"}
        )
        auto_executable = plan is not None and (
            tier == "high"
            or (low_tier_short_circuit and tier == "mid")
        )

        decision = RouterDecision(
            question=question,
            problem_type=classifier_result.problem_type,
            confidence=classifier_result.problem_type_confidence,
            tier=tier,
            auto_executable=auto_executable,
            reasoning=classifier_result.reasoning,
            plan=plan,
            adjustments=adjustments,
            raw_router={
                "recommended_protocol": classifier_result.recommended_protocol,
                "recommended_name": classifier_result.recommended_name,
                "alternatives": [
                    {"protocol": a.protocol, "name": a.name, "reason": a.reason}
                    for a in classifier_result.alternatives
                ],
                "cost_tier": classifier_result.cost_tier,
                "features": classifier_result.features,
                "timings": classifier_result.timings,
            },
        )
        _router_cache_put(cache_key, decision)
        return decision

    def _tier(self, confidence: int) -> str:
        if confidence >= self.high_threshold:
            return "high"
        if confidence >= self.mid_threshold:
            return "mid"
        return "low"
