"""P13: Ecocycle Planning — Lifecycle stage mapping orchestrator.

Map a portfolio of initiatives to lifecycle stages (Birth, Maturity,
Creative Destruction, Renewal), build consensus, generate stage-appropriate
action plans.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import anthropic

from .prompts import (
    ASSESS_INITIATIVES_PROMPT,
    RESOLVE_CONTESTED_PROMPT,
    ACTION_PLAN_PROMPT,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

VALID_STAGES = {"birth", "maturity", "destruction", "renewal"}


@dataclass
class InitiativeAssessment:
    """One agent's assessment of one initiative."""
    agent_name: str
    initiative: str
    stage: str
    reasoning: str


@dataclass
class EcocycleResult:
    """Complete result from an Ecocycle Planning run."""
    question: str
    initiatives: list[str]
    agent_assessments: list[InitiativeAssessment]
    consensus_stages: dict[str, str]          # initiative -> stage
    contested: list[str]                       # initiatives that required resolution
    action_plans: dict[str, list[str]]         # initiative -> actions
    portfolio_summary: str
    timings: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class EcocyclePlanningOrchestrator:
    """Runs the three-phase Ecocycle Planning protocol."""

    thinking_model: str = "claude-opus-4-6"
    orchestration_model: str = "claude-haiku-4-5-20251001"

    def __init__(
        self,
        agents: list[dict[str, str]],
        *,
        thinking_model: str | None = None,
        orchestration_model: str | None = None,
    ) -> None:
        self.agents = agents  # [{"name": ..., "system_prompt": ...}, ...]
        if thinking_model:
            self.thinking_model = thinking_model
        if orchestration_model:
            self.orchestration_model = orchestration_model
        self.client = anthropic.AsyncAnthropic()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def run(self, question: str, initiatives: list[str]) -> EcocycleResult:
        timings: dict[str, float] = {}

        # Phase 1 — Assess: each agent assigns lifecycle stages (parallel, Opus)
        t0 = time.time()
        agent_assessments = await self._assess_initiatives(question, initiatives)
        timings["phase1_assess"] = round(time.time() - t0, 2)

        # Phase 2 — Consensus: aggregate votes, resolve contested
        t0 = time.time()
        consensus_stages, contested = self._build_consensus(initiatives, agent_assessments)
        # Resolve contested initiatives via Haiku
        if contested:
            resolutions = await self._resolve_contested(question, contested, agent_assessments)
            for initiative, stage in resolutions.items():
                consensus_stages[initiative] = stage
        timings["phase2_consensus"] = round(time.time() - t0, 2)

        # Phase 3 — Action Plan: generate stage-appropriate actions (Opus)
        t0 = time.time()
        action_plans, portfolio_summary = await self._generate_action_plans(
            question, initiatives, consensus_stages,
        )
        timings["phase3_action_plan"] = round(time.time() - t0, 2)

        return EcocycleResult(
            question=question,
            initiatives=initiatives,
            agent_assessments=agent_assessments,
            consensus_stages=consensus_stages,
            contested=contested,
            action_plans=action_plans,
            portfolio_summary=portfolio_summary,
            timings=timings,
        )

    # ------------------------------------------------------------------
    # Phase 1: Assess Initiatives
    # ------------------------------------------------------------------

    async def _assess_initiatives(
        self, question: str, initiatives: list[str],
    ) -> list[InitiativeAssessment]:
        """Each agent assigns each initiative to a lifecycle stage (parallel, Opus)."""
        initiatives_block = "\n".join(f"- {init}" for init in initiatives)

        async def _one(agent: dict) -> list[InitiativeAssessment]:
            prompt = ASSESS_INITIATIVES_PROMPT.format(
                question=question,
                agent_name=agent["name"],
                system_prompt=agent["system_prompt"],
                initiatives_block=initiatives_block,
            )
            resp = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = self._parse_json_object(self._extract_text(resp))
            results = []
            for a in parsed.get("assessments", []):
                stage = a.get("stage", "").lower().strip()
                if stage not in VALID_STAGES:
                    stage = "renewal"  # safe fallback
                results.append(InitiativeAssessment(
                    agent_name=agent["name"],
                    initiative=a.get("initiative", ""),
                    stage=stage,
                    reasoning=a.get("reasoning", ""),
                ))
            return results

        batches = await asyncio.gather(*[_one(a) for a in self.agents])
        return [item for batch in batches for item in batch]

    # ------------------------------------------------------------------
    # Phase 2: Build Consensus
    # ------------------------------------------------------------------

    @staticmethod
    def _build_consensus(
        initiatives: list[str],
        assessments: list[InitiativeAssessment],
    ) -> tuple[dict[str, str], list[str]]:
        """Aggregate votes per initiative. >50% agreement = consensus, else contested."""
        consensus: dict[str, str] = {}
        contested: list[str] = []

        for initiative in initiatives:
            votes = [
                a.stage for a in assessments
                if a.initiative.lower().strip() == initiative.lower().strip()
            ]
            if not votes:
                contested.append(initiative)
                continue

            counter = Counter(votes)
            top_stage, top_count = counter.most_common(1)[0]
            if top_count > len(votes) / 2:
                consensus[initiative] = top_stage
            else:
                contested.append(initiative)

        return consensus, contested

    async def _resolve_contested(
        self,
        question: str,
        contested: list[str],
        assessments: list[InitiativeAssessment],
    ) -> dict[str, str]:
        """Use Haiku to resolve contested initiatives."""

        async def _resolve_one(initiative: str) -> tuple[str, str]:
            relevant = [
                a for a in assessments
                if a.initiative.lower().strip() == initiative.lower().strip()
            ]
            votes_block = "\n".join(
                f"- {a.agent_name} voted **{a.stage}**: {a.reasoning}"
                for a in relevant
            )
            prompt = RESOLVE_CONTESTED_PROMPT.format(
                question=question,
                initiative=initiative,
                votes_block=votes_block,
            )
            resp = await self.client.messages.create(
                model=self.orchestration_model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = self._parse_json_object(self._extract_text(resp))
            stage = parsed.get("stage", "renewal").lower().strip()
            if stage not in VALID_STAGES:
                stage = "renewal"
            return initiative, stage

        results = await asyncio.gather(*[_resolve_one(i) for i in contested])
        return dict(results)

    # ------------------------------------------------------------------
    # Phase 3: Action Plans
    # ------------------------------------------------------------------

    async def _generate_action_plans(
        self,
        question: str,
        initiatives: list[str],
        consensus_stages: dict[str, str],
    ) -> tuple[dict[str, list[str]], str]:
        """Generate stage-appropriate actions for each initiative (Opus)."""
        portfolio_block = "\n".join(
            f"- **{init}** → {consensus_stages.get(init, 'unknown').upper()}"
            for init in initiatives
        )
        prompt = ACTION_PLAN_PROMPT.format(
            question=question,
            portfolio_block=portfolio_block,
        )
        resp = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}],
        )
        parsed = self._parse_json_object(self._extract_text(resp))
        action_plans = parsed.get("action_plans", {})
        portfolio_summary = parsed.get("portfolio_summary", "")
        return action_plans, portfolio_summary

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
