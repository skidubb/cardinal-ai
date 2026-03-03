"""P0c: Tiered Escalation — Orchestrator.

Route queries to the simplest adequate tier first. If confidence is low
or errors detected, escalate to progressively more rigorous protocols.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

import anthropic
from protocols.llm import extract_text, parse_json_object, filter_exceptions

from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from .prompts import (
    TIER1_AGENT_PROMPT,
    TIER1_CONFIDENCE_PROMPT,
    TIER2_AGENT_PROMPT,
    TIER2_SYNTHESIS_PROMPT,
    TIER3_REBUTTAL_PROMPT,
    TIER3_OVERSIGHT_PROMPT,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TierResult:
    tier: int
    response: str
    confidence: int
    reasoning: str


@dataclass
class EscalationResult:
    question: str
    final_tier: int
    tier_results: list[TierResult]
    final_response: str
    flagged_for_human: bool
    flag_reason: str | None
    timings: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Default agents
# ---------------------------------------------------------------------------

DEFAULT_AGENTS = [
    {"name": "CEO", "system_prompt": "You are a CEO focused on strategy, vision, and competitive positioning."},
    {"name": "CFO", "system_prompt": "You are a CFO focused on financial analysis, risk, and capital allocation."},
    {"name": "CTO", "system_prompt": "You are a CTO focused on technology strategy, architecture, and innovation."},
]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class TieredEscalation:
    """Runs the three-tier escalation meta-protocol."""

    thinking_model: str = THINKING_MODEL
    orchestration_model: str = ORCHESTRATION_MODEL

    def __init__(
        self,
        agents: list[dict[str, str]] | None = None,
        *,
        thinking_model: str | None = None,
        orchestration_model: str | None = None,
        confidence_threshold: int = 80,
        consensus_threshold: float = 0.7,
    ) -> None:
        self.agents = agents or DEFAULT_AGENTS
        if thinking_model:
            self.thinking_model = thinking_model
        if orchestration_model:
            self.orchestration_model = orchestration_model
        self.confidence_threshold = confidence_threshold
        self.consensus_threshold = consensus_threshold
        self.client = anthropic.AsyncAnthropic()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def run(self, question: str) -> EscalationResult:
        timings: dict[str, float] = {}
        tier_results: list[TierResult] = []

        # Tier 1 — Single agent fast response
        t0 = time.time()
        tier1 = await self._tier1(question)
        timings["tier1"] = time.time() - t0
        tier_results.append(tier1)

        if tier1.confidence >= self.confidence_threshold:
            return EscalationResult(
                question=question,
                final_tier=1,
                tier_results=tier_results,
                final_response=tier1.response,
                flagged_for_human=False,
                flag_reason=None,
                timings=timings,
            )

        # Tier 2 — Multi-agent parallel + synthesis
        t0 = time.time()
        tier2, agent_responses = await self._tier2(question)
        timings["tier2"] = time.time() - t0
        tier_results.append(tier2)

        if tier2.confidence >= int(self.consensus_threshold * 100):
            return EscalationResult(
                question=question,
                final_tier=2,
                tier_results=tier_results,
                final_response=tier2.response,
                flagged_for_human=False,
                flag_reason=None,
                timings=timings,
            )

        # Tier 3 — Debate + oversight
        t0 = time.time()
        tier3, flagged, flag_reason = await self._tier3(
            question, tier1, tier2, agent_responses,
        )
        timings["tier3"] = time.time() - t0
        tier_results.append(tier3)

        return EscalationResult(
            question=question,
            final_tier=3,
            tier_results=tier_results,
            final_response=tier3.response,
            flagged_for_human=flagged,
            flag_reason=flag_reason,
            timings=timings,
        )

    # ------------------------------------------------------------------
    # Tier 1: Fast single-agent
    # ------------------------------------------------------------------

    async def _tier1(self, question: str) -> TierResult:
        # Get response from single agent (Opus)
        prompt = TIER1_AGENT_PROMPT.format(question=question)
        resp = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = extract_text(resp)

        # Evaluate confidence (Haiku)
        conf_prompt = TIER1_CONFIDENCE_PROMPT.format(
            question=question, response=response_text,
        )
        conf_resp = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=256,
            messages=[{"role": "user", "content": conf_prompt}],
        )
        conf = parse_json_object(extract_text(conf_resp))

        return TierResult(
            tier=1,
            response=response_text,
            confidence=conf.get("confidence", 0),
            reasoning=conf.get("reasoning", ""),
        )

    # ------------------------------------------------------------------
    # Tier 2: Multi-agent parallel + synthesis
    # ------------------------------------------------------------------

    async def _tier2(
        self, question: str,
    ) -> tuple[TierResult, dict[str, str]]:
        # Parallel agent responses (Opus)
        async def _one(agent: dict) -> tuple[str, str]:
            prompt = TIER2_AGENT_PROMPT.format(
                question=question,
                agent_name=agent["name"],
                system_prompt=agent["system_prompt"],
            )
            resp = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return agent["name"], extract_text(resp)

        results = await asyncio.gather(*[_one(a) for a in self.agents], return_exceptions=True)
        results = filter_exceptions(results, label="p0c_tiered_escalation")
        agent_responses = {name: text for name, text in results}

        # Synthesis (Haiku)
        responses_block = "\n\n".join(
            f"### {name}\n{text}" for name, text in agent_responses.items()
        )
        synth_prompt = TIER2_SYNTHESIS_PROMPT.format(
            question=question, responses_block=responses_block,
        )
        synth_resp = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": synth_prompt}],
        )
        synth = parse_json_object(extract_text(synth_resp))

        consensus_score = synth.get("consensus_score", 0.0)
        tier_result = TierResult(
            tier=2,
            response=synth.get("synthesis", ""),
            confidence=int(consensus_score * 100),
            reasoning=synth.get("reasoning", ""),
        )
        return tier_result, agent_responses

    # ------------------------------------------------------------------
    # Tier 3: Debate + oversight
    # ------------------------------------------------------------------

    async def _tier3(
        self,
        question: str,
        tier1: TierResult,
        tier2: TierResult,
        agent_responses: dict[str, str],
    ) -> tuple[TierResult, bool, str | None]:
        # Rebuttal round (Opus, parallel)
        async def _rebuttal(agent: dict) -> tuple[str, str]:
            own = agent_responses.get(agent["name"], "")
            others = "\n\n".join(
                f"### {name}\n{text}"
                for name, text in agent_responses.items()
                if name != agent["name"]
            )
            prompt = TIER3_REBUTTAL_PROMPT.format(
                question=question,
                agent_name=agent["name"],
                system_prompt=agent["system_prompt"],
                own_response=own,
                synthesis=tier2.response,
                other_responses_block=others,
            )
            resp = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            return agent["name"], extract_text(resp)

        rebuttal_results = await asyncio.gather(
            *[_rebuttal(a) for a in self.agents],
            return_exceptions=True,
        )
        rebuttal_results = filter_exceptions(rebuttal_results, label="p0c_tiered_escalation")
        rebuttals = {name: text for name, text in rebuttal_results}

        # Oversight (Haiku)
        rebuttals_block = "\n\n".join(
            f"### {name}\n{text}" for name, text in rebuttals.items()
        )
        oversight_prompt = TIER3_OVERSIGHT_PROMPT.format(
            question=question,
            tier1_response=tier1.response,
            tier2_synthesis=tier2.response,
            rebuttals_block=rebuttals_block,
        )
        oversight_resp = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": oversight_prompt}],
        )
        oversight = parse_json_object(extract_text(oversight_resp))

        passes = oversight.get("passes_safety_check", False)
        final_response = oversight.get("final_response", tier2.response)
        flag_reason = oversight.get("flag_reason") if not passes else None

        tier_result = TierResult(
            tier=3,
            response=final_response,
            confidence=oversight.get("confidence", 0),
            reasoning=f"Safety check: {'passed' if passes else 'failed'}",
        )
        return tier_result, not passes, flag_reason

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------


