"""P08: Min Specs — Identify the minimum set of rules needed for a goal.

Generate all specs, deduplicate, test each for essentiality, vote on borderlines,
then synthesize the minimum viable specification set.
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
    GENERATE_SPECS_PROMPT,
    DEDUP_SPECS_PROMPT,
    ELIMINATION_TEST_PROMPT,
    BORDERLINE_VOTE_PROMPT,
    FINAL_SYNTHESIS_PROMPT,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Spec:
    id: str
    description: str


@dataclass
class EliminationVerdict:
    spec_id: str
    verdict: str  # MUST_HAVE, REMOVABLE, BORDERLINE
    reasoning: str = ""


@dataclass
class BorderlineVote:
    spec_id: str
    agent_name: str
    vote: str  # KEEP or REMOVE
    rationale: str = ""


@dataclass
class MinSpecsResult:
    question: str
    all_specs: list[Spec]
    must_haves: list[Spec]
    eliminated: list[Spec]
    borderline_votes: list[BorderlineVote]
    final_min_specs: list[Spec]
    synthesis: str
    timings: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class MinSpecsOrchestrator:
    """Runs the five-phase Min Specs protocol."""

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

    async def run(self, question: str) -> MinSpecsResult:
        timings: dict[str, float] = {}

        # Phase 1 — Generate Specs (parallel, Opus with thinking)
        t0 = time.time()
        raw_specs = await self._generate_specs(question)
        timings["phase1_generate"] = round(time.time() - t0, 2)

        # Phase 2 — Union & Deduplicate (Haiku)
        t0 = time.time()
        all_specs = await self._deduplicate(question, raw_specs)
        timings["phase2_dedup"] = round(time.time() - t0, 2)

        # Phase 3 — Elimination Test (parallel per spec, Haiku)
        t0 = time.time()
        verdicts = await self._elimination_test(question, all_specs)
        must_haves: list[Spec] = []
        eliminated: list[Spec] = []
        borderlines: list[Spec] = []
        for spec in all_specs:
            v = next((v for v in verdicts if v.spec_id == spec.id), None)
            if v is None or v.verdict == "MUST_HAVE":
                must_haves.append(spec)
            elif v.verdict == "REMOVABLE":
                eliminated.append(spec)
            else:
                borderlines.append(spec)
        timings["phase3_eliminate"] = round(time.time() - t0, 2)

        # Phase 4 — Borderline Vote (parallel per spec x agent, Haiku)
        t0 = time.time()
        all_votes: list[BorderlineVote] = []
        if borderlines:
            all_votes = await self._borderline_vote(question, borderlines, must_haves)
            # Tally votes per spec — majority wins
            for spec in borderlines:
                spec_votes = [v for v in all_votes if v.spec_id == spec.id]
                keeps = sum(1 for v in spec_votes if v.vote == "KEEP")
                removes = sum(1 for v in spec_votes if v.vote == "REMOVE")
                if keeps >= removes:
                    must_haves.append(spec)
                else:
                    eliminated.append(spec)
        timings["phase4_vote"] = round(time.time() - t0, 2)

        # Phase 5 — Final Synthesis (Opus with thinking)
        t0 = time.time()
        synthesis = await self._final_synthesis(
            question, all_specs, must_haves, eliminated, all_votes,
        )
        timings["phase5_synthesis"] = round(time.time() - t0, 2)

        return MinSpecsResult(
            question=question,
            all_specs=all_specs,
            must_haves=must_haves,
            eliminated=eliminated,
            borderline_votes=all_votes,
            final_min_specs=must_haves,
            synthesis=synthesis,
            timings=timings,
        )

    # ------------------------------------------------------------------
    # Phase 1: Generate Specs
    # ------------------------------------------------------------------

    async def _generate_specs(self, question: str) -> list[dict]:
        """Each agent generates specs in parallel (Opus with thinking)."""

        async def _one(agent: dict) -> list[dict]:
            prompt = GENERATE_SPECS_PROMPT.format(
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
            parsed = self._parse_json_object(_extract_text(resp))
            return parsed.get("specs", [])

        results = await asyncio.gather(*[_one(a) for a in self.agents])
        return [s for batch in results for s in batch]

    # ------------------------------------------------------------------
    # Phase 2: Deduplicate
    # ------------------------------------------------------------------

    async def _deduplicate(self, question: str, raw_specs: list[dict]) -> list[Spec]:
        """Merge and deduplicate all specs (Haiku)."""
        specs_block = "\n".join(
            f"- {s.get('id', '?')}: {s.get('description', '?')}" for s in raw_specs
        )
        prompt = DEDUP_SPECS_PROMPT.format(
            question=question,
            all_specs_block=specs_block,
        )
        resp = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        parsed = self._parse_json_object(_extract_text(resp))
        return [
            Spec(id=s.get("id", f"S{i+1}"), description=s.get("description", ""))
            for i, s in enumerate(parsed.get("specs", []))
        ]

    # ------------------------------------------------------------------
    # Phase 3: Elimination Test
    # ------------------------------------------------------------------

    async def _elimination_test(
        self, question: str, specs: list[Spec],
    ) -> list[EliminationVerdict]:
        """Test each spec: would removing it make the purpose impossible? (Haiku, parallel)."""

        async def _test_one(spec: Spec) -> EliminationVerdict:
            prompt = ELIMINATION_TEST_PROMPT.format(
                question=question,
                spec_id=spec.id,
                spec_description=spec.description,
            )
            resp = await self.client.messages.create(
                model=self.orchestration_model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = self._parse_json_object(_extract_text(resp))
            return EliminationVerdict(
                spec_id=spec.id,
                verdict=parsed.get("verdict", "BORDERLINE").upper(),
                reasoning=parsed.get("reasoning", ""),
            )

        sem = asyncio.Semaphore(8)

        async def _throttled(spec: Spec) -> EliminationVerdict:
            async with sem:
                return await _test_one(spec)

        return await asyncio.gather(*[_throttled(s) for s in specs])

    # ------------------------------------------------------------------
    # Phase 4: Borderline Vote
    # ------------------------------------------------------------------

    async def _borderline_vote(
        self,
        question: str,
        borderlines: list[Spec],
        must_haves: list[Spec],
    ) -> list[BorderlineVote]:
        """Agents vote on borderline specs (Haiku, parallel per spec x agent)."""
        must_have_block = "\n".join(
            f"- {s.id}: {s.description}" for s in must_haves
        ) or "None confirmed yet."

        async def _vote_one(agent: dict, spec: Spec) -> BorderlineVote:
            prompt = BORDERLINE_VOTE_PROMPT.format(
                question=question,
                agent_name=agent["name"],
                system_prompt=agent["system_prompt"],
                spec_id=spec.id,
                spec_description=spec.description,
                must_have_block=must_have_block,
            )
            resp = await self.client.messages.create(
                model=self.orchestration_model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = self._parse_json_object(_extract_text(resp))
            return BorderlineVote(
                spec_id=spec.id,
                agent_name=agent["name"],
                vote=parsed.get("vote", "KEEP").upper(),
                rationale=parsed.get("rationale", ""),
            )

        sem = asyncio.Semaphore(8)

        async def _throttled(agent: dict, spec: Spec) -> BorderlineVote:
            async with sem:
                return await _vote_one(agent, spec)

        tasks = [_throttled(a, s) for s in borderlines for a in self.agents]
        return await asyncio.gather(*tasks)

    # ------------------------------------------------------------------
    # Phase 5: Final Synthesis
    # ------------------------------------------------------------------

    async def _final_synthesis(
        self,
        question: str,
        all_specs: list[Spec],
        must_haves: list[Spec],
        eliminated: list[Spec],
        borderline_votes: list[BorderlineVote],
    ) -> str:
        """Produce final synthesis (Opus with thinking)."""
        must_have_block = "\n".join(
            f"- {s.id}: {s.description}" for s in must_haves
        ) or "None"

        eliminated_block = "\n".join(
            f"- {s.id}: {s.description}" for s in eliminated
        ) or "None"

        # Build borderline summary
        borderline_specs_ids = set(v.spec_id for v in borderline_votes)
        borderline_lines = []
        for sid in sorted(borderline_specs_ids):
            votes = [v for v in borderline_votes if v.spec_id == sid]
            keeps = sum(1 for v in votes if v.vote == "KEEP")
            removes = sum(1 for v in votes if v.vote == "REMOVE")
            outcome = "KEPT" if keeps >= removes else "REMOVED"
            spec_desc = next(
                (s.description for s in all_specs if s.id == sid), "?"
            )
            borderline_lines.append(
                f"- {sid}: {spec_desc} -> {outcome} ({keeps} keep / {removes} remove)"
            )
        borderline_block = "\n".join(borderline_lines) or "None — no borderline specs."

        prompt = FINAL_SYNTHESIS_PROMPT.format(
            question=question,
            total_specs=len(all_specs),
            must_have_block=must_have_block,
            eliminated_block=eliminated_block,
            borderline_block=borderline_block,
        )

        resp = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=16_000,
            thinking={
                "type": "enabled",
                "budget_tokens": self.thinking_budget,
            },
            messages=[{"role": "user", "content": prompt}],
        )
        return _extract_text(resp)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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


def _extract_text(response: anthropic.types.Message) -> str:
    """Pull plain text from an Anthropic API response."""
    for block in response.content:
        if hasattr(block, "text"):
            return block.text
    return ""
