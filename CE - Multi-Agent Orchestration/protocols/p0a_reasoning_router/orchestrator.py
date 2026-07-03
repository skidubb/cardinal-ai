"""P0a: Reasoning Router — Orchestrator.

Classify a question's problem type and recommend the optimal coordination protocol.
This is a meta-protocol: it does NOT execute the selected protocol.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

import anthropic
from protocols.langfuse_tracing import trace_protocol, create_span, end_span
from protocols.llm import extract_text, llm_complete, parse_json_object

from protocols.registry import build_routing_prompt_section
from protocols.router_weights import (
    format_for_prompt as format_weights_for_prompt,
    performance_by_protocol,
    suggest_override,
)
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from .prompts import (
    FEATURE_EXTRACTION_PROMPT,
    PROBLEM_TYPE_PROMPT,
    ROUTING_DECISION_PROMPT,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Alternative:
    protocol: str
    name: str
    reason: str


@dataclass
class RouterResult:
    question: str
    features: dict[str, Any]
    problem_type: str
    problem_type_confidence: int
    recommended_protocol: str
    recommended_name: str
    alternatives: list[Alternative]
    reasoning: str
    cost_tier: str
    timings: dict[str, float] = field(default_factory=dict)
    historical_performance: list[dict[str, Any]] = field(default_factory=list)
    weights_override_applied: bool = False
    weights_override_rationale: str = ""
    llm_recommendation: str = ""


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class ReasoningRouter:
    """Runs the four-phase routing meta-protocol."""

    thinking_model: str = THINKING_MODEL
    orchestration_model: str = ORCHESTRATION_MODEL

    def __init__(
        self,
        *,
        thinking_model: str | None = None,
        orchestration_model: str | None = None,
    ) -> None:
        if thinking_model:
            self.thinking_model = thinking_model
        if orchestration_model:
            self.orchestration_model = orchestration_model
        self.client = anthropic.AsyncAnthropic()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    @trace_protocol("p0a_reasoning_router")
    async def run(self, question: str) -> RouterResult:
        timings: dict[str, float] = {}

        # Phase 1 — Feature Extraction (Haiku)
        t0 = time.time()
        span = create_span("stage:feature_extraction", {})
        try:
            features = await self._extract_features(question)
            end_span(span, output="features extracted")
        except Exception:
            end_span(span, error="feature_extraction failed")
            raise
        timings["phase1_features"] = time.time() - t0

        # Phase 2 — Problem Type Classification (Haiku)
        t0 = time.time()
        span = create_span("stage:problem_type_classification", {})
        try:
            classification = await self._classify_problem_type(question, features)
            end_span(span, output=f"type={classification.get('problem_type', 'unknown')}")
        except Exception:
            end_span(span, error="problem_type_classification failed")
            raise
        timings["phase2_classify"] = time.time() - t0

        # Phase 3 — Protocol Selection (Haiku), informed by historical weights
        problem_type = classification.get("problem_type", "General Analysis")
        perf = performance_by_protocol(problem_type)
        weights_context = format_weights_for_prompt(perf)

        t0 = time.time()
        span = create_span(
            "stage:protocol_selection",
            {"has_weights": bool(perf), "weight_count": len(perf)},
        )
        try:
            routing = await self._select_protocol(
                question, features, classification, weights_context
            )
            end_span(span, output=f"recommended={routing.get('recommended_protocol', 'unknown')}")
        except Exception:
            end_span(span, error="protocol_selection failed")
            raise
        timings["phase3_select"] = time.time() - t0

        # Phase 3b — Post-hoc override from historical performance (best-effort)
        llm_choice = routing.get("recommended_protocol", "P3")
        final_choice = llm_choice
        override_rationale = ""
        override, rationale = suggest_override(llm_choice, perf)
        if override:
            final_choice = override
            override_rationale = rationale or ""
            span = create_span(
                "stage:weights_override",
                {"from": llm_choice, "to": override},
            )
            end_span(span, output=override_rationale)

        # Phase 4 — Assemble result
        t0 = time.time()
        alternatives = [
            Alternative(
                protocol=alt.get("protocol", ""),
                name=alt.get("name", ""),
                reason=alt.get("reason", ""),
            )
            for alt in routing.get("alternatives", [])
        ]
        timings["phase4_assemble"] = time.time() - t0

        return RouterResult(
            question=question,
            features=features,
            problem_type=problem_type,
            problem_type_confidence=classification.get("confidence", 50),
            recommended_protocol=final_choice,
            recommended_name=routing.get("recommended_name", "Parallel Synthesis"),
            alternatives=alternatives,
            reasoning=routing.get("reasoning", ""),
            cost_tier=routing.get("cost_tier", "low"),
            timings=timings,
            historical_performance=[p.as_dict() for p in perf.values()],
            weights_override_applied=bool(override),
            weights_override_rationale=override_rationale,
            llm_recommendation=llm_choice,
        )

    # ------------------------------------------------------------------
    # Phase 1: Feature Extraction
    # ------------------------------------------------------------------

    async def _extract_features(self, question: str) -> dict[str, Any]:
        prompt = FEATURE_EXTRACTION_PROMPT.format(question=question)
        resp = await llm_complete(
            self.client,
            model=self.orchestration_model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
            agent_name="feature_extraction",
        )
        return parse_json_object(extract_text(resp))

    # ------------------------------------------------------------------
    # Phase 2: Problem Type Classification
    # ------------------------------------------------------------------

    async def _classify_problem_type(
        self, question: str, features: dict[str, Any]
    ) -> dict[str, Any]:
        prompt = PROBLEM_TYPE_PROMPT.format(
            question=question,
            features_json=json.dumps(features, indent=2),
        )
        resp = await llm_complete(
            self.client,
            model=self.orchestration_model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
            agent_name="problem_type_classification",
        )
        return parse_json_object(extract_text(resp))

    # ------------------------------------------------------------------
    # Phase 3: Protocol Selection
    # ------------------------------------------------------------------

    async def _select_protocol(
        self,
        question: str,
        features: dict[str, Any],
        classification: dict[str, Any],
        weights_context: str = "",
    ) -> dict[str, Any]:
        history_block = (
            f"\n\n{weights_context}\n\n"
            "Weight this history against the rules — a protocol with strong historical "
            "performance for this problem type is a stronger candidate."
            if weights_context
            else ""
        )
        prompt = ROUTING_DECISION_PROMPT.format(
            question=question,
            features_json=json.dumps(features, indent=2),
            problem_type=classification.get("problem_type", "General Analysis"),
            confidence=classification.get("confidence", 50),
            type_reasoning=classification.get("reasoning", ""),
            protocol_mapping=build_routing_prompt_section() + history_block,
        )
        resp = await llm_complete(
            self.client,
            model=self.orchestration_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
            agent_name="protocol_selection",
        )
        return parse_json_object(extract_text(resp))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------


