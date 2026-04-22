"""Adaptive Router Orchestrator — classify + resolve + (optionally) execute.

The orchestrator itself only decides. Execution is the caller's job (CLI or API
runner). This keeps the router composable: it can be used from a chain, a
notebook, or a future scheduler without coupling to the FastAPI runner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from protocols.p0a_reasoning_router.orchestrator import ReasoningRouter, RouterResult

from .resolver import Resolver, ResolveResult


# Confidence thresholds — tunable via constructor
DEFAULT_HIGH = 80
DEFAULT_MID = 50


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
    ) -> RouterDecision:
        """Classify the question and return a decision.

        Does not raise on low confidence — returns a decision with
        auto_executable=False. Callers choose whether to prompt the user
        or abort.
        """
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

        return RouterDecision(
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

    def _tier(self, confidence: int) -> str:
        if confidence >= self.high_threshold:
            return "high"
        if confidence >= self.mid_threshold:
            return "mid"
        return "low"
