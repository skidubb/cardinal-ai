"""P11: Discovery & Action Dialogue (DAD) — Positive deviant identification orchestrator."""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

import anthropic

from .prompts import (
    SCOUT_DEVIANTS_PROMPT,
    FILTER_BEHAVIOR_PROMPT,
    EXTRACT_PRACTICES_PROMPT,
    ADAPT_RECOMMENDATIONS_PROMPT,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DADResult:
    """Complete result from a Discovery & Action Dialogue run."""
    question: str
    scouted_deviants: list[dict[str, Any]]
    filtered_behaviors: list[dict[str, Any]]
    extracted_practices: list[dict[str, Any]]
    adapted_recommendations: str
    timings: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class DADOrchestrator:
    """Runs the four-phase Discovery & Action Dialogue protocol."""

    thinking_model: str = "claude-opus-4-6"
    orchestration_model: str = "claude-haiku-4-5-20251001"

    def __init__(
        self,
        agents: list[dict[str, str]],
        *,
        thinking_model: str | None = None,
        orchestration_model: str | None = None,
        thinking_budget: int = 10_000,
    ) -> None:
        self.agents = agents  # [{"name": ..., "system_prompt": ...}, ...]
        if thinking_model:
            self.thinking_model = thinking_model
        if orchestration_model:
            self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def run(self, question: str) -> DADResult:
        timings: dict[str, float] = {}

        # Phase 1 — Scout positive deviants (parallel, Opus)
        t0 = time.time()
        scouted_deviants = await self._scout_deviants(question)
        timings["phase1_scout"] = round(time.time() - t0, 2)

        # Phase 2 — Filter behaviors (parallel, Haiku)
        t0 = time.time()
        filtered_behaviors = await self._filter_behaviors(question, scouted_deviants)
        timings["phase2_filter"] = round(time.time() - t0, 2)

        # Phase 3 — Extract transferable practices (Haiku)
        t0 = time.time()
        extracted_practices = await self._extract_practices(question, filtered_behaviors)
        timings["phase3_extract"] = round(time.time() - t0, 2)

        # Phase 4 — Adapt recommendations (Opus)
        t0 = time.time()
        adapted_recommendations = await self._adapt_recommendations(question, extracted_practices)
        timings["phase4_adapt"] = round(time.time() - t0, 2)

        return DADResult(
            question=question,
            scouted_deviants=scouted_deviants,
            filtered_behaviors=filtered_behaviors,
            extracted_practices=extracted_practices,
            adapted_recommendations=adapted_recommendations,
            timings=timings,
        )

    # ------------------------------------------------------------------
    # Phase 1: Scout Positive Deviants
    # ------------------------------------------------------------------

    async def _scout_deviants(self, question: str) -> list[dict[str, Any]]:
        """Each agent identifies positive deviants in parallel (Opus with thinking)."""

        async def _one(agent: dict) -> list[dict]:
            prompt = SCOUT_DEVIANTS_PROMPT.format(
                question=question,
                agent_name=agent["name"],
                system_prompt=agent["system_prompt"],
            )
            resp = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=self.thinking_budget + 4096,
                thinking={
                    "type": "enabled",
                    "budget_tokens": self.thinking_budget,
                },
                system=agent["system_prompt"],
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = self._parse_json_object(self._extract_text(resp))
            deviants = parsed.get("deviants", [])
            # Tag each deviant with the source agent
            for d in deviants:
                d["source_agent"] = agent["name"]
            return deviants

        results = await asyncio.gather(*[_one(a) for a in self.agents])
        return [d for batch in results for d in batch]

    # ------------------------------------------------------------------
    # Phase 2: Filter Behaviors
    # ------------------------------------------------------------------

    async def _filter_behaviors(
        self,
        question: str,
        deviants: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Test each behavior against uncommon/accessible/evidence criteria (Haiku, parallel)."""

        async def _filter_one(deviant: dict) -> dict[str, Any] | None:
            prompt = FILTER_BEHAVIOR_PROMPT.format(
                question=question,
                deviant=deviant.get("deviant", ""),
                behavior=deviant.get("behavior", ""),
                why_it_works=deviant.get("why_it_works", ""),
            )
            resp = await self.client.messages.create(
                model=self.orchestration_model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = self._parse_json_object(self._extract_text(resp))
            parsed["source_agent"] = deviant.get("source_agent", "")
            if parsed.get("passes", False):
                return parsed
            return None

        sem = asyncio.Semaphore(8)

        async def _throttled(d):
            async with sem:
                return await _filter_one(d)

        results = await asyncio.gather(*[_throttled(d) for d in deviants])
        return [r for r in results if r is not None]

    # ------------------------------------------------------------------
    # Phase 3: Extract Transferable Practices
    # ------------------------------------------------------------------

    async def _extract_practices(
        self,
        question: str,
        filtered: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Extract core transferable practices from surviving behaviors (Haiku)."""
        if not filtered:
            return []

        behaviors_block = "\n".join(
            f"- **{b.get('deviant', 'Unknown')}**: {b.get('behavior', '')} "
            f"(why: {b.get('why_it_works', b.get('evidence_reasoning', ''))})"
            for b in filtered
        )

        prompt = EXTRACT_PRACTICES_PROMPT.format(
            question=question,
            behaviors_block=behaviors_block,
        )
        resp = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        parsed = self._parse_json_object(self._extract_text(resp))
        return parsed.get("practices", [])

    # ------------------------------------------------------------------
    # Phase 4: Adapt Recommendations
    # ------------------------------------------------------------------

    async def _adapt_recommendations(
        self,
        question: str,
        practices: list[dict[str, Any]],
    ) -> str:
        """Synthesize practices into adapted recommendations (Opus with thinking)."""
        if not practices:
            return "No transferable practices survived filtering."

        practices_block = "\n\n".join(
            f"**{p.get('practice', 'Unnamed')}**\n"
            f"  Description: {p.get('description', '')}\n"
            f"  Derived from: {', '.join(p.get('derived_from', []))}\n"
            f"  Mechanism: {p.get('mechanism', '')}"
            for p in practices
        )

        prompt = ADAPT_RECOMMENDATIONS_PROMPT.format(
            question=question,
            practices_block=practices_block,
        )
        resp = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 8192,
            thinking={
                "type": "enabled",
                "budget_tokens": self.thinking_budget,
            },
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
