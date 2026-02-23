"""P23: Cynefin Probe-Sense-Respond — Orchestrator.

Classify the situation into a Cynefin domain, then apply the domain-appropriate
decision approach (Sense-Categorize-Respond, Sense-Analyze-Respond,
Probe-Sense-Respond, Act-Sense-Respond, or Decompose).
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
    DOMAIN_CLASSIFICATION_PROMPT,
    CLEAR_RESPONSE_PROMPT,
    COMPLICATED_RESPONSE_PROMPT,
    COMPLEX_RESPONSE_PROMPT,
    CHAOTIC_RESPONSE_PROMPT,
    CONFUSED_RESPONSE_PROMPT,
    SYNTHESIS_PROMPT,
)

# Valid Cynefin domains
VALID_DOMAINS = {"clear", "complicated", "complex", "chaotic", "confused"}

# Map domain -> prompt template
DOMAIN_PROMPTS = {
    "clear": CLEAR_RESPONSE_PROMPT,
    "complicated": COMPLICATED_RESPONSE_PROMPT,
    "complex": COMPLEX_RESPONSE_PROMPT,
    "chaotic": CHAOTIC_RESPONSE_PROMPT,
    "confused": CONFUSED_RESPONSE_PROMPT,
}

# Map domain -> model tier (clear uses Haiku, everything else uses Opus)
DOMAIN_MODELS = {
    "clear": "orchestration",
    "complicated": "thinking",
    "complex": "thinking",
    "chaotic": "thinking",
    "confused": "thinking",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DomainVote:
    agent_name: str
    domain: str
    reasoning: str
    confidence: int


@dataclass
class CynefinResult:
    question: str
    domain_votes: list[DomainVote]
    consensus_domain: str
    was_contested: bool
    domain_responses: dict[str, Any]  # agent_name -> parsed response
    action_plan: dict[str, Any]
    timings: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class CynefinOrchestrator:
    """Runs the four-phase Cynefin Probe-Sense-Respond protocol."""

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

    async def run(self, question: str) -> CynefinResult:
        timings: dict[str, float] = {}

        # Phase 1 — Domain Classification (parallel, Opus)
        t0 = time.time()
        domain_votes = await self._classify_domain(question)
        timings["phase1_classify"] = time.time() - t0

        # Phase 2 — Consensus
        t0 = time.time()
        consensus_domain, was_contested = await self._resolve_consensus(
            question, domain_votes,
        )
        timings["phase2_consensus"] = time.time() - t0

        # Phase 3 — Domain-Appropriate Response (parallel)
        t0 = time.time()
        domain_responses = await self._domain_response(question, consensus_domain)
        timings["phase3_response"] = time.time() - t0

        # Phase 4 — Synthesis (Opus)
        t0 = time.time()
        action_plan = await self._synthesize(
            question, consensus_domain, was_contested,
            domain_votes, domain_responses,
        )
        timings["phase4_synthesis"] = time.time() - t0

        return CynefinResult(
            question=question,
            domain_votes=domain_votes,
            consensus_domain=consensus_domain,
            was_contested=was_contested,
            domain_responses=domain_responses,
            action_plan=action_plan,
            timings=timings,
        )

    # ------------------------------------------------------------------
    # Phase 1: Domain Classification
    # ------------------------------------------------------------------

    async def _classify_domain(self, question: str) -> list[DomainVote]:
        """Each agent independently classifies the Cynefin domain (Opus, parallel)."""

        async def _one(agent: dict) -> DomainVote:
            prompt = DOMAIN_CLASSIFICATION_PROMPT.format(
                question=question,
                agent_name=agent["name"],
                system_prompt=agent["system_prompt"],
            )
            resp = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = self._parse_json_object(self._extract_text(resp))
            domain = parsed.get("domain", "confused").lower().strip()
            if domain not in VALID_DOMAINS:
                domain = "confused"
            return DomainVote(
                agent_name=agent["name"],
                domain=domain,
                reasoning=parsed.get("reasoning", ""),
                confidence=int(parsed.get("confidence", 50)),
            )

        results = await asyncio.gather(*[_one(a) for a in self.agents])
        return list(results)

    # ------------------------------------------------------------------
    # Phase 2: Consensus
    # ------------------------------------------------------------------

    async def _resolve_consensus(
        self,
        question: str,
        votes: list[DomainVote],
    ) -> tuple[str, bool]:
        """Aggregate domain votes. Majority wins; ties default to 'confused'."""
        domain_counts = Counter(v.domain for v in votes)
        total = len(votes)

        # Check for clear majority (> 50%)
        top_domain, top_count = domain_counts.most_common(1)[0]
        if top_count > total / 2:
            # Check if contested (any dissent)
            was_contested = top_count < total
            return top_domain, was_contested

        # No majority — use Haiku to tiebreak with reasoning context
        top_two = domain_counts.most_common(2)
        if len(top_two) >= 2 and top_two[0][1] == top_two[1][1]:
            # True tie — default to confused (need more probing)
            return "confused", True

        # Plurality but not majority — still contested
        return top_domain, True

    # ------------------------------------------------------------------
    # Phase 3: Domain-Appropriate Response
    # ------------------------------------------------------------------

    async def _domain_response(
        self,
        question: str,
        domain: str,
    ) -> dict[str, Any]:
        """Each agent provides a domain-appropriate response (parallel)."""
        prompt_template = DOMAIN_PROMPTS[domain]
        model_tier = DOMAIN_MODELS[domain]
        model = (
            self.orchestration_model
            if model_tier == "orchestration"
            else self.thinking_model
        )
        max_tokens = 1024 if domain == "clear" else 2048

        async def _one(agent: dict) -> tuple[str, dict]:
            prompt = prompt_template.format(
                question=question,
                agent_name=agent["name"],
                system_prompt=agent["system_prompt"],
            )
            resp = await self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = self._parse_json_object(self._extract_text(resp))
            return agent["name"], parsed

        results = await asyncio.gather(*[_one(a) for a in self.agents])
        return {name: data for name, data in results}

    # ------------------------------------------------------------------
    # Phase 4: Synthesis
    # ------------------------------------------------------------------

    async def _synthesize(
        self,
        question: str,
        consensus_domain: str,
        was_contested: bool,
        domain_votes: list[DomainVote],
        domain_responses: dict[str, Any],
    ) -> dict[str, Any]:
        domain_votes_block = "\n".join(
            f"- {v.agent_name}: **{v.domain}** (confidence: {v.confidence}%) — {v.reasoning}"
            for v in domain_votes
        )

        responses_block = "\n\n".join(
            f"### {name}\n```json\n{json.dumps(data, indent=2)}\n```"
            for name, data in domain_responses.items()
        )

        prompt = SYNTHESIS_PROMPT.format(
            question=question,
            consensus_domain=consensus_domain,
            was_contested="Yes — agents disagreed on classification" if was_contested else "No — unanimous agreement",
            domain_votes_block=domain_votes_block,
            responses_block=responses_block,
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
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Try to find JSON block
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        # Try to find raw braces
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {}
