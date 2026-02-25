"""P21: Interests-Based Negotiation — Orchestrator.

Surface interests, map shared/compatible/conflicting, generate mutual-gains options,
evaluate Pareto-optimality, synthesize agreement.
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
    SURFACE_INTERESTS_PROMPT,
    INTEREST_MAP_PROMPT,
    GENERATE_OPTIONS_PROMPT,
    SCORE_OPTIONS_PROMPT,
    FINAL_AGREEMENT_PROMPT,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Interest:
    agent: str
    interest: str
    priority: str  # high, medium, low
    type: str  # need, fear, aspiration


@dataclass
class NegotiationResult:
    question: str
    interest_maps: dict[str, list[dict[str, Any]]]  # per agent
    categorized_interests: dict[str, Any]  # shared/compatible/conflicting
    generated_options: list[dict[str, Any]]
    option_scores: list[dict[str, Any]]
    selected_agreement: dict[str, Any]
    interest_satisfaction: dict[str, float]  # agent -> satisfaction 0-1
    timings: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class InterestsNegotiationOrchestrator:
    """Runs the four-phase Interests-Based Negotiation protocol."""

    thinking_model: str = "claude-opus-4-6"
    orchestration_model: str = "claude-haiku-4-5-20251001"

    def __init__(
        self,
        agents: list[dict[str, str]],
        *,
        thinking_model: str | None = None,
        orchestration_model: str | None = None,
        max_rounds: int = 2,
    ) -> None:
        self.agents = agents  # [{"name": ..., "system_prompt": ...}, ...]
        if thinking_model:
            self.thinking_model = thinking_model
        if orchestration_model:
            self.orchestration_model = orchestration_model
        self.max_rounds = max_rounds
        self.client = anthropic.AsyncAnthropic()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def run(self, question: str) -> NegotiationResult:
        timings: dict[str, float] = {}

        # Phase 1 — Surface Interests (parallel, Opus)
        t0 = time.time()
        interest_maps = await self._surface_interests(question)
        timings["phase1_surface_interests"] = round(time.time() - t0, 2)

        # Phase 2 — Interest Map (Haiku mediator)
        t0 = time.time()
        categorized = await self._build_interest_map(question, interest_maps)
        timings["phase2_interest_map"] = round(time.time() - t0, 2)

        # Phase 3 — Generate Options (parallel, Opus) — may run multiple rounds
        all_options: list[dict[str, Any]] = []
        all_scores: list[dict[str, Any]] = []
        pareto_found = False

        for round_num in range(1, self.max_rounds + 1):
            t0 = time.time()
            options = await self._generate_options(question, categorized)
            timings[f"phase3_generate_r{round_num}"] = round(time.time() - t0, 2)

            all_options.extend(options)

            # Phase 4 — Score & check Pareto (Haiku scoring)
            t0 = time.time()
            scores = await self._score_options(question, all_options, interest_maps)
            timings[f"phase4_score_r{round_num}"] = round(time.time() - t0, 2)
            all_scores = scores

            pareto_found = any(s.get("pareto_optimal") for s in scores)
            if pareto_found:
                break

        # Final synthesis (Opus)
        t0 = time.time()
        agreement = await self._synthesize_agreement(
            question, categorized, all_options, all_scores,
        )
        timings["phase5_agreement"] = round(time.time() - t0, 2)

        # Extract satisfaction scores
        satisfaction: dict[str, float] = {}
        agreement_body = agreement.get("agreement", {})
        for agent_name, info in agreement_body.get("interest_satisfaction", {}).items():
            if isinstance(info, dict):
                satisfaction[agent_name] = info.get("score", 0.0)
            elif isinstance(info, (int, float)):
                satisfaction[agent_name] = float(info)

        return NegotiationResult(
            question=question,
            interest_maps=interest_maps,
            categorized_interests=categorized,
            generated_options=all_options,
            option_scores=all_scores,
            selected_agreement=agreement,
            interest_satisfaction=satisfaction,
            timings=timings,
        )

    # ------------------------------------------------------------------
    # Phase 1: Surface Interests
    # ------------------------------------------------------------------

    async def _surface_interests(
        self, question: str,
    ) -> dict[str, list[dict[str, Any]]]:
        """Each agent independently surfaces underlying interests (Opus)."""

        async def _one(agent: dict) -> tuple[str, list[dict]]:
            prompt = SURFACE_INTERESTS_PROMPT.format(
                question=question,
                agent_name=agent["name"],
                system_prompt=agent["system_prompt"],
            )
            resp = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = self._parse_json_object(self._extract_text(resp))
            return agent["name"], parsed.get("interests", [])

        results = await asyncio.gather(*[_one(a) for a in self.agents])
        return {name: interests for name, interests in results}

    # ------------------------------------------------------------------
    # Phase 2: Build Interest Map
    # ------------------------------------------------------------------

    async def _build_interest_map(
        self,
        question: str,
        interest_maps: dict[str, list[dict]],
    ) -> dict[str, Any]:
        """Mediator categorizes interests as shared/compatible/conflicting (Haiku)."""
        interests_block = self._format_interests_block(interest_maps)
        prompt = INTEREST_MAP_PROMPT.format(
            question=question,
            interests_block=interests_block,
        )
        resp = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._parse_json_object(self._extract_text(resp))

    # ------------------------------------------------------------------
    # Phase 3: Generate Options
    # ------------------------------------------------------------------

    async def _generate_options(
        self,
        question: str,
        categorized: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Each agent brainstorms mutual-gains options (Opus, parallel)."""
        shared_block = self._format_category(categorized.get("shared", []))
        compatible_block = self._format_category(categorized.get("compatible", []))
        conflicting_block = self._format_category(categorized.get("conflicting", []))

        async def _one(agent: dict) -> list[dict]:
            prompt = GENERATE_OPTIONS_PROMPT.format(
                question=question,
                agent_name=agent["name"],
                system_prompt=agent["system_prompt"],
                shared_block=shared_block,
                compatible_block=compatible_block,
                conflicting_block=conflicting_block,
            )
            resp = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = self._parse_json_object(self._extract_text(resp))
            opts = parsed.get("options", [])
            for opt in opts:
                opt["proposed_by"] = agent["name"]
            return opts

        results = await asyncio.gather(*[_one(a) for a in self.agents])
        return [opt for batch in results for opt in batch]

    # ------------------------------------------------------------------
    # Phase 4: Score Options
    # ------------------------------------------------------------------

    async def _score_options(
        self,
        question: str,
        options: list[dict[str, Any]],
        interest_maps: dict[str, list[dict]],
    ) -> list[dict[str, Any]]:
        """Score each option against all agents' interests (Haiku)."""
        options_block = "\n".join(
            f"Option {i}: {opt.get('option', opt.get('description', ''))}"
            for i, opt in enumerate(options)
        )
        interests_block = self._format_interests_block(interest_maps)

        prompt = SCORE_OPTIONS_PROMPT.format(
            question=question,
            options_block=options_block,
            interests_block=interests_block,
        )
        resp = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        parsed = self._parse_json_object(self._extract_text(resp))
        return parsed.get("scores", [])

    # ------------------------------------------------------------------
    # Phase 5: Synthesize Agreement
    # ------------------------------------------------------------------

    async def _synthesize_agreement(
        self,
        question: str,
        categorized: dict[str, Any],
        options: list[dict[str, Any]],
        scores: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Opus synthesizes the final agreement."""
        shared_block = self._format_category(categorized.get("shared", []))
        compatible_block = self._format_category(categorized.get("compatible", []))
        conflicting_block = self._format_category(categorized.get("conflicting", []))

        scored_block = []
        pareto_block = []
        for s in scores:
            idx = s.get("option_index", "?")
            opt_text = options[idx].get("option", "") if isinstance(idx, int) and idx < len(options) else "?"
            agent_scores = s.get("agent_scores", {})
            score_str = ", ".join(f"{k}: {v.get('score', '?')}" for k, v in agent_scores.items()) if isinstance(agent_scores, dict) else str(agent_scores)
            line = f"Option {idx}: {opt_text} — Scores: {score_str}"
            scored_block.append(line)
            if s.get("pareto_optimal"):
                pareto_block.append(line)

        prompt = FINAL_AGREEMENT_PROMPT.format(
            question=question,
            shared_block=shared_block,
            compatible_block=compatible_block,
            conflicting_block=conflicting_block,
            scored_options_block="\n".join(scored_block) or "None",
            pareto_block="\n".join(pareto_block) or "No Pareto-optimal options found",
        )
        resp = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._parse_json_object(self._extract_text(resp))

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

    @staticmethod
    def _format_interests_block(interest_maps: dict[str, list[dict]]) -> str:
        lines = []
        for agent_name, interests in interest_maps.items():
            lines.append(f"\n**{agent_name}:**")
            for i in interests:
                priority = i.get("priority", "?")
                itype = i.get("type", "?")
                lines.append(f"  - [{priority}/{itype}] {i.get('interest', '')}")
        return "\n".join(lines)

    @staticmethod
    def _format_category(items: list) -> str:
        if not items:
            return "None"
        lines = []
        for item in items:
            if isinstance(item, dict):
                lines.append(f"  - {json.dumps(item, default=str)}")
            else:
                lines.append(f"  - {item}")
        return "\n".join(lines)
