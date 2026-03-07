"""P26: Crazy Eights — Orchestrator.

Rapid divergent ideation: 8 ideas per agent, cluster, dot vote, develop winners.
"""

from __future__ import annotations

import asyncio
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import anthropic
from protocols.langfuse_tracing import trace_protocol, create_span, end_span
from protocols.llm import extract_text, llm_complete, parse_json_object, filter_exceptions

from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from .prompts import (
    RAPID_GENERATION_PROMPT,
    CLUSTER_PROMPT,
    DOT_VOTE_PROMPT,
    DEVELOP_CONCEPTS_PROMPT,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CrazyEightsResult:
    question: str
    raw_ideas: dict[str, list[str]]  # agent_name -> list of 8 ideas
    total_ideas: int
    clusters: list[dict[str, Any]]
    vote_tally: dict[str, int]  # idea text -> vote count
    top_ideas: list[str]
    developed_concepts: list[dict[str, Any]]
    timings: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class CrazyEightsOrchestrator:
    """Runs the four-phase Crazy Eights protocol."""

    thinking_model: str = THINKING_MODEL
    orchestration_model: str = ORCHESTRATION_MODEL

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

    @trace_protocol("p26_crazy_eights")
    async def run(self, question: str) -> CrazyEightsResult:
        timings: dict[str, float] = {}

        # Phase 1 — Rapid Generation (Opus, parallel, low max_tokens)
        span = create_span("stage:rapid_generation", {"agent_count": len(self.agents)})
        try:
            t0 = time.time()
            raw_ideas = await self._rapid_generation(question)
            timings["phase1_generate"] = time.time() - t0
            total_gen = sum(len(v) for v in raw_ideas.values())
            end_span(span, output=f"{total_gen} ideas from {len(raw_ideas)} agents")
        except Exception:
            end_span(span, error="rapid_generation failed")
            raise

        # Flatten all ideas
        all_ideas = [idea for ideas in raw_ideas.values() for idea in ideas]
        total_ideas = len(all_ideas)

        # Phase 2 — Cluster (Haiku)
        span = create_span("stage:cluster", {"total_ideas": total_ideas})
        try:
            t0 = time.time()
            clusters = await self._cluster(question, all_ideas, total_ideas)
            timings["phase2_cluster"] = time.time() - t0
            end_span(span, output=f"{len(clusters)} clusters")
        except Exception:
            end_span(span, error="cluster failed")
            raise

        # Phase 3 — Dot Vote (Haiku, parallel)
        span = create_span("stage:dot_vote", {"agent_count": len(self.agents)})
        try:
            t0 = time.time()
            vote_tally, top_ideas = await self._dot_vote(question, raw_ideas, clusters)
            timings["phase3_vote"] = time.time() - t0
            end_span(span, output=f"{len(top_ideas)} top ideas from {len(vote_tally)} voted")
        except Exception:
            end_span(span, error="dot_vote failed")
            raise

        # Phase 4 — Develop Top Concepts (Opus)
        span = create_span("stage:develop_concepts", {"top_idea_count": len(top_ideas)})
        try:
            t0 = time.time()
            developed_concepts = await self._develop_concepts(
                question, top_ideas, total_ideas,
            )
            timings["phase4_develop"] = time.time() - t0
            end_span(span, output=f"{len(developed_concepts)} developed concepts")
        except Exception:
            end_span(span, error="develop_concepts failed")
            raise

        return CrazyEightsResult(
            question=question,
            raw_ideas=raw_ideas,
            total_ideas=total_ideas,
            clusters=clusters,
            vote_tally=vote_tally,
            top_ideas=top_ideas,
            developed_concepts=developed_concepts,
            timings=timings,
        )

    # ------------------------------------------------------------------
    # Phase 1: Rapid Generation
    # ------------------------------------------------------------------

    async def _rapid_generation(self, question: str) -> dict[str, list[str]]:
        """Each agent generates exactly 8 ideas in parallel (Opus, low tokens)."""

        async def _one(agent: dict) -> tuple[str, list[str]]:
            prompt = RAPID_GENERATION_PROMPT.format(
                question=question,
                agent_name=agent["name"],
                system_prompt=agent["system_prompt"],
            )
            resp = await llm_complete(
                self.client,
                model=self.thinking_model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
                agent_name=agent["name"],
            )
            parsed = parse_json_object(extract_text(resp))
            ideas = parsed.get("ideas", [])
            # Enforce exactly 8
            ideas = [str(i).strip() for i in ideas if str(i).strip()][:8]
            return agent["name"], ideas

        results = await asyncio.gather(*[_one(a) for a in self.agents], return_exceptions=True)
        results = filter_exceptions(results, label="p26_crazy_eights")
        return {name: ideas for name, ideas in results}

    # ------------------------------------------------------------------
    # Phase 2: Cluster
    # ------------------------------------------------------------------

    async def _cluster(
        self, question: str, all_ideas: list[str], total_ideas: int,
    ) -> list[dict[str, Any]]:
        ideas_block = "\n".join(f"- {idea}" for idea in all_ideas)
        prompt = CLUSTER_PROMPT.format(
            question=question,
            total_ideas=total_ideas,
            ideas_block=ideas_block,
        )
        resp = await llm_complete(
            self.client,
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            agent_name="cluster",
        )
        parsed = parse_json_object(extract_text(resp))
        return parsed.get("clusters", [])

    # ------------------------------------------------------------------
    # Phase 3: Dot Vote
    # ------------------------------------------------------------------

    async def _dot_vote(
        self,
        question: str,
        raw_ideas: dict[str, list[str]],
        clusters: list[dict[str, Any]],
    ) -> tuple[dict[str, int], list[str]]:
        """Each agent casts 3 votes (not for own ideas). Returns tally + top ideas."""

        clusters_block = ""
        for c in clusters:
            clusters_block += f"\n**{c.get('theme', 'Unnamed')}**:\n"
            for idea in c.get("ideas", []):
                clusters_block += f"  - {idea}\n"

        async def _one(agent: dict) -> list[dict[str, str]]:
            own_ideas = raw_ideas.get(agent["name"], [])
            own_ideas_block = "\n".join(f"  - {i}" for i in own_ideas) or "  (none)"
            prompt = DOT_VOTE_PROMPT.format(
                question=question,
                agent_name=agent["name"],
                system_prompt=agent["system_prompt"],
                clusters_block=clusters_block,
                own_ideas_block=own_ideas_block,
            )
            resp = await llm_complete(
                self.client,
                model=self.orchestration_model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
                agent_name=agent["name"],
            )
            parsed = parse_json_object(extract_text(resp))
            votes = parsed.get("votes", [])
            # Enforce exactly 3
            return votes[:3]

        results = await asyncio.gather(*[_one(a) for a in self.agents], return_exceptions=True)
        results = filter_exceptions(results, label="p26_crazy_eights")

        # Tally votes
        tally: Counter[str] = Counter()
        for agent_votes in results:
            for v in agent_votes:
                idea_text = v.get("idea", "").strip()
                if idea_text:
                    tally[idea_text] += 1

        # Top 3-5 ideas (at least 3, include ties up to 5)
        sorted_ideas = tally.most_common()
        if not sorted_ideas:
            return dict(tally), []

        top_ideas: list[str] = []
        cutoff_votes = 0
        for i, (idea, count) in enumerate(sorted_ideas):
            if i < 3:
                top_ideas.append(idea)
                cutoff_votes = count
            elif i < 5 and count >= cutoff_votes:
                top_ideas.append(idea)
            else:
                break

        return dict(tally), top_ideas

    # ------------------------------------------------------------------
    # Phase 4: Develop Top Concepts
    # ------------------------------------------------------------------

    async def _develop_concepts(
        self,
        question: str,
        top_ideas: list[str],
        total_ideas: int,
    ) -> list[dict[str, Any]]:
        if not top_ideas:
            return []

        top_ideas_block = "\n".join(f"- {idea}" for idea in top_ideas)
        prompt = DEVELOP_CONCEPTS_PROMPT.format(
            question=question,
            total_ideas=total_ideas,
            top_ideas_block=top_ideas_block,
        )
        resp = await llm_complete(
            self.client,
            model=self.thinking_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            agent_name="develop_concepts",
        )
        parsed = parse_json_object(extract_text(resp))
        return parsed.get("developed_concepts", [])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------


