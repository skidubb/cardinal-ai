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
from protocols.llm import extract_text, parse_json_object

from protocols.registry import build_routing_prompt_section
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

    async def run(self, question: str) -> RouterResult:
        timings: dict[str, float] = {}

        # Phase 1 — Feature Extraction (Haiku)
        t0 = time.time()
        features = await self._extract_features(question)
        timings["phase1_features"] = time.time() - t0

        # Phase 2 — Problem Type Classification (Haiku)
        t0 = time.time()
        classification = await self._classify_problem_type(question, features)
        timings["phase2_classify"] = time.time() - t0

        # Phase 3 — Protocol Selection (Haiku)
        t0 = time.time()
        routing = await self._select_protocol(question, features, classification)
        timings["phase3_select"] = time.time() - t0

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
            problem_type=classification.get("problem_type", "General Analysis"),
            problem_type_confidence=classification.get("confidence", 50),
            recommended_protocol=routing.get("recommended_protocol", "P3"),
            recommended_name=routing.get("recommended_name", "Parallel Synthesis"),
            alternatives=alternatives,
            reasoning=routing.get("reasoning", ""),
            cost_tier=routing.get("cost_tier", "low"),
            timings=timings,
        )

    # ------------------------------------------------------------------
    # Phase 1: Feature Extraction
    # ------------------------------------------------------------------

    async def _extract_features(self, question: str) -> dict[str, Any]:
        prompt = FEATURE_EXTRACTION_PROMPT.format(question=question)
        resp = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
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
        resp = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
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
    ) -> dict[str, Any]:
        prompt = ROUTING_DECISION_PROMPT.format(
            question=question,
            features_json=json.dumps(features, indent=2),
            problem_type=classification.get("problem_type", "General Analysis"),
            confidence=classification.get("confidence", 50),
            type_reasoning=classification.get("reasoning", ""),
            protocol_mapping=build_routing_prompt_section(),
        )
        resp = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return parse_json_object(extract_text(resp))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------


