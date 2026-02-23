"""P0b: Cost-Aware Skip Gate — Orchestrator.

Decide whether a question warrants a full multi-agent pipeline or a simple
single-agent response, balancing accuracy vs. cost.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

import anthropic

from .prompts import (
    FEATURE_EXTRACTION_PROMPT,
    GATE_DECISION_PROMPT,
    SINGLE_AGENT_PROMPT,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SkipGateResult:
    question: str
    features: dict[str, Any]
    decision: str  # "skip" or "escalate"
    confidence: int
    reasoning: str
    estimated_cost_savings: str
    single_agent_response: str | None
    recommended_protocol: str | None
    recommended_name: str | None
    timings: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class SkipGate:
    """Runs the cost-aware skip gate meta-protocol."""

    thinking_model: str = "claude-opus-4-6"
    orchestration_model: str = "claude-haiku-4-5-20251001"

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

    async def run(self, question: str) -> SkipGateResult:
        timings: dict[str, float] = {}

        # Phase 1 — Feature Extraction (Haiku)
        t0 = time.time()
        features = await self._extract_features(question)
        timings["phase1_features"] = time.time() - t0

        # Phase 2 — Gate Decision (Haiku)
        t0 = time.time()
        gate = await self._gate_decision(question, features)
        timings["phase2_gate"] = time.time() - t0

        decision = gate.get("decision", "escalate")
        single_agent_response = None
        recommended_protocol = gate.get("recommended_protocol")
        recommended_name = gate.get("recommended_name")

        # Phase 3 — Execute based on decision
        if decision == "skip":
            t0 = time.time()
            single_agent_response = await self._single_agent_response(question)
            timings["phase3_single_agent"] = time.time() - t0
            recommended_protocol = None
            recommended_name = None

        return SkipGateResult(
            question=question,
            features=features,
            decision=decision,
            confidence=gate.get("confidence", 50),
            reasoning=gate.get("reasoning", ""),
            estimated_cost_savings=gate.get("estimated_cost_savings", "low"),
            single_agent_response=single_agent_response,
            recommended_protocol=recommended_protocol,
            recommended_name=recommended_name,
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
        return self._parse_json_object(self._extract_text(resp))

    # ------------------------------------------------------------------
    # Phase 2: Gate Decision
    # ------------------------------------------------------------------

    async def _gate_decision(
        self, question: str, features: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = GATE_DECISION_PROMPT.format(
            question=question,
            features_json=json.dumps(features, indent=2),
        )
        resp = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._parse_json_object(self._extract_text(resp))

    # ------------------------------------------------------------------
    # Phase 3: Single Agent Response (only if skipped)
    # ------------------------------------------------------------------

    async def _single_agent_response(self, question: str) -> str:
        prompt = SINGLE_AGENT_PROMPT.format(question=question)
        resp = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._extract_text(resp)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text(response: anthropic.types.Message) -> str:
        parts = []
        for block in response.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "\n".join(parts)

    @staticmethod
    def _parse_json_object(text: str) -> dict:
        """Extract the first JSON object from text."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {}
