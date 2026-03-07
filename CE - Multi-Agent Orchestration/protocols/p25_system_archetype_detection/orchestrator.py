"""P25: System Archetype Detection — Orchestrator.

Match observed dynamics to known system archetypes (Fixes That Fail,
Shifting the Burden, Limits to Growth, etc.) and recommend interventions.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import anthropic
from protocols.langfuse_tracing import trace_protocol, create_span, end_span
from protocols.llm import agent_complete, extract_text, llm_complete, parse_json_object, filter_exceptions

from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from .prompts import (
    DYNAMICS_OBSERVATION_PROMPT,
    DYNAMICS_MERGE_PROMPT,
    ARCHETYPE_MATCHING_PROMPT,
    SYNTHESIS_PROMPT,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ObservedDynamic:
    id: str
    pattern: str
    description: str


@dataclass
class ArchetypeMatch:
    archetype: str
    score: int
    structural_mapping: dict[str, str]
    reasoning: str


@dataclass
class ArchetypeResult:
    question: str
    observed_dynamics: list[ObservedDynamic]
    archetype_scores: dict[str, float]
    best_matches: list[ArchetypeMatch]
    interventions: list[dict[str, str]]
    timings: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class ArchetypeDetector:
    """Runs the four-phase System Archetype Detection protocol."""

    thinking_model: str = THINKING_MODEL
    orchestration_model: str = ORCHESTRATION_MODEL

    def __init__(
        self,
        agents: list[dict[str, str]],
        *,
        thinking_model: str | None = None,
        orchestration_model: str | None = None,
    ) -> None:
        self.agents = agents
        if thinking_model:
            self.thinking_model = thinking_model
        if orchestration_model:
            self.orchestration_model = orchestration_model
        self.client = anthropic.AsyncAnthropic()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    @trace_protocol("p25_system_archetype_detection")
    async def run(self, question: str) -> ArchetypeResult:
        timings: dict[str, float] = {}

        # Phase 1 — Observe Dynamics (parallel, Opus)
        span = create_span("stage:observe_dynamics", {"agent_count": len(self.agents)})
        try:
            t0 = time.time()
            raw_dynamics = await self._observe_dynamics(question)
            timings["phase1_observe"] = time.time() - t0
            end_span(span, output=f"{len(raw_dynamics)} raw dynamics")
        except Exception:
            end_span(span, error="observe_dynamics failed")
            raise

        # Phase 2 — Merge Dynamics (Haiku)
        span = create_span("stage:merge_dynamics", {"raw_count": len(raw_dynamics)})
        try:
            t0 = time.time()
            dynamics = await self._merge_dynamics(question, raw_dynamics)
            timings["phase2_merge"] = time.time() - t0
            end_span(span, output=f"{len(dynamics)} merged dynamics")
        except Exception:
            end_span(span, error="merge_dynamics failed")
            raise

        # Phase 3 — Match Archetypes (parallel, Opus)
        span = create_span("stage:match_archetypes", {"dynamic_count": len(dynamics)})
        try:
            t0 = time.time()
            raw_scores = await self._match_archetypes(question, dynamics)
            timings["phase3_match"] = time.time() - t0
            end_span(span, output=f"{len(raw_scores)} agent score sets")
        except Exception:
            end_span(span, error="match_archetypes failed")
            raise

        # Aggregate scores across agents
        archetype_scores = self._aggregate_scores(raw_scores)

        # Phase 4 — Synthesize (Opus)
        span = create_span("stage:synthesize", {"archetype_count": len(archetype_scores)})
        try:
            t0 = time.time()
            synthesis = await self._synthesize(question, dynamics, archetype_scores)
            timings["phase4_synthesize"] = time.time() - t0
            end_span(span, output="synthesis complete")
        except Exception:
            end_span(span, error="synthesize failed")
            raise

        best_matches = [
            ArchetypeMatch(
                archetype=m.get("archetype", ""),
                score=m.get("score", 0),
                structural_mapping=m.get("structural_mapping", {}),
                reasoning=m.get("reasoning", ""),
            )
            for m in synthesis.get("best_matches", [])
        ]

        return ArchetypeResult(
            question=question,
            observed_dynamics=dynamics,
            archetype_scores=archetype_scores,
            best_matches=best_matches,
            interventions=synthesis.get("interventions", []),
            timings=timings,
        )

    # ------------------------------------------------------------------
    # Phase 1: Observe Dynamics
    # ------------------------------------------------------------------

    async def _observe_dynamics(self, question: str) -> list[dict]:
        async def _one(agent: dict) -> list[dict]:
            prompt = DYNAMICS_OBSERVATION_PROMPT.format(
                question=question,
                agent_name=agent["name"],
                system_prompt=agent["system_prompt"],
            )
            text = await agent_complete(
                agent=agent,
                fallback_model=self.thinking_model,
                messages=[{"role": "user", "content": prompt}],
                thinking_budget=0,
                max_tokens=2048,
                anthropic_client=self.client,
            )
            parsed = parse_json_object(text)
            return parsed.get("dynamics", [])

        results = await asyncio.gather(*[_one(a) for a in self.agents], return_exceptions=True)
        results = filter_exceptions(results, label="p25_system_archetype_detection")
        return [d for batch in results for d in batch]

    # ------------------------------------------------------------------
    # Phase 2: Merge Dynamics
    # ------------------------------------------------------------------

    async def _merge_dynamics(
        self, question: str, raw_dynamics: list[dict],
    ) -> list[ObservedDynamic]:
        raw_block = "\n".join(
            f"- {d.get('pattern', '???')}: {d.get('description', '')}"
            for d in raw_dynamics
        )
        prompt = DYNAMICS_MERGE_PROMPT.format(
            question=question,
            raw_dynamics_block=raw_block,
        )
        resp = await llm_complete(
            self.client,
            model=self.orchestration_model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
            agent_name="merge_dynamics",
        )
        parsed = parse_json_object(extract_text(resp))
        return [
            ObservedDynamic(
                id=d.get("id", ""),
                pattern=d.get("pattern", ""),
                description=d.get("description", ""),
            )
            for d in parsed.get("dynamics", [])
        ]

    # ------------------------------------------------------------------
    # Phase 3: Match Archetypes
    # ------------------------------------------------------------------

    async def _match_archetypes(
        self, question: str, dynamics: list[ObservedDynamic],
    ) -> list[list[dict]]:
        dynamics_block = "\n".join(
            f"- {d.id}: {d.pattern} — {d.description}" for d in dynamics
        )

        async def _one(agent: dict) -> list[dict]:
            prompt = ARCHETYPE_MATCHING_PROMPT.format(
                question=question,
                agent_name=agent["name"],
                system_prompt=agent["system_prompt"],
                dynamics_block=dynamics_block,
            )
            text = await agent_complete(
                agent=agent,
                fallback_model=self.thinking_model,
                messages=[{"role": "user", "content": prompt}],
                thinking_budget=0,
                max_tokens=2048,
                anthropic_client=self.client,
            )
            parsed = parse_json_object(text)
            return parsed.get("scores", [])

        results = await asyncio.gather(*[_one(a) for a in self.agents], return_exceptions=True)
        results = filter_exceptions(results, label="p25_system_archetype_detection")
        return list(results)

    # ------------------------------------------------------------------
    # Score aggregation
    # ------------------------------------------------------------------

    @staticmethod
    def _aggregate_scores(raw_scores: list[list[dict]]) -> dict[str, float]:
        totals: dict[str, list[float]] = {}
        for agent_scores in raw_scores:
            for entry in agent_scores:
                name = entry.get("archetype", "")
                score = entry.get("score", 0)
                totals.setdefault(name, []).append(float(score))
        return {
            name: round(sum(scores) / len(scores), 1)
            for name, scores in totals.items()
            if scores
        }

    # ------------------------------------------------------------------
    # Phase 4: Synthesize
    # ------------------------------------------------------------------

    async def _synthesize(
        self,
        question: str,
        dynamics: list[ObservedDynamic],
        archetype_scores: dict[str, float],
    ) -> dict[str, Any]:
        dynamics_block = "\n".join(
            f"- {d.id}: {d.pattern} — {d.description}" for d in dynamics
        )
        scores_block = "\n".join(
            f"- {name}: {score}/100"
            for name, score in sorted(
                archetype_scores.items(), key=lambda x: x[1], reverse=True,
            )
        )
        prompt = SYNTHESIS_PROMPT.format(
            question=question,
            dynamics_block=dynamics_block,
            scores_block=scores_block,
        )
        proxy_agent = self.agents[0] if self.agents else {"name": "synthesizer", "system_prompt": ""}
        text = await agent_complete(
            agent=proxy_agent,
            fallback_model=self.thinking_model,
            messages=[{"role": "user", "content": prompt}],
            thinking_budget=0,
            max_tokens=4096,
            anthropic_client=self.client,
        )
        return parse_json_object(text)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------


