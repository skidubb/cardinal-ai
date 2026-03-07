"""P6: TRIZ Inversion Protocol — Agent-agnostic orchestrator.

"What would guarantee failure?" → invert failures into solutions.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path

from protocols.llm import agent_complete, extract_text, llm_complete, parse_json_array, filter_exceptions
from protocols.synthesis import SynthesisEngine
from protocols.tracing import make_client
from protocols.langfuse_tracing import trace_protocol, create_span, end_span
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from .prompts import (
    DEDUPLICATION_PROMPT,
    FAILURE_GENERATION_PROMPT,
    INVERSION_PROMPT,
    RANKING_PROMPT,
    SYNTHESIS_PROMPT,
)


@dataclass
class FailureMode:
    id: int
    title: str
    description: str
    category: str
    severity: int = 0
    likelihood: int = 0
    composite: int = 0
    rationale: str = ""


@dataclass
class Solution:
    failure_id: int
    title: str
    description: str


@dataclass
class TRIZResult:
    question: str
    failure_modes: list[FailureMode] = field(default_factory=list)
    solutions: list[Solution] = field(default_factory=list)
    synthesis: str = ""
    agent_contributions: dict[str, list[str]] = field(default_factory=dict)


class TRIZOrchestrator:
    """Runs the 6-stage TRIZ Inversion protocol with any set of agents."""

    def __init__(
        self,
        agents: list[dict],
        thinking_model: str = THINKING_MODEL,
        orchestration_model: str = ORCHESTRATION_MODEL,
        thinking_budget: int = 10_000,
        trace: bool = False,
        trace_path: str | None = None,
        synthesis_engine: SynthesisEngine | None = None,
    ):
        """
        Args:
            agents: List of {"name": str, "system_prompt": str} dicts.
                    Any agents work — C-Suite, GTM, custom, etc.
            thinking_model: Model for agent reasoning (failure gen, synthesis).
            orchestration_model: Model for mechanical steps (dedup, invert, rank).
            thinking_budget: Token budget for extended thinking on Opus calls.
            trace: Enable JSONL execution tracing.
            synthesis_engine: Optional SynthesisEngine instance.
        """
        if not agents:
            raise ValueError("At least one agent is required")
        self.agents = agents
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.client = make_client(protocol_id="p06_triz", trace=trace, trace_path=Path(trace_path) if trace_path else None)
        self._synth = synthesis_engine or SynthesisEngine(
            self.client, thinking_model, thinking_budget, use_agent=True
        )

    @trace_protocol("p06_triz")
    async def run(self, question: str) -> TRIZResult:
        """Execute the full TRIZ Inversion protocol."""
        result = TRIZResult(question=question)

        # Stage 1: Reframe (implicit — the prompt does this)
        # Stage 2: Parallel failure generation
        print("Stage 2: Generating failure modes...")
        span = create_span("stage:failure_generation", {"agent_count": len(self.agents)})
        try:
            raw_failures = await self._generate_failures(question)
            result.agent_contributions = {
                agent["name"]: raw_failures[i]
                for i, agent in enumerate(self.agents)
            }
            end_span(span, output=f"{len(raw_failures)} failure sets")
        except Exception:
            end_span(span, error="failure_generation failed")
            raise

        # Stage 3: Deduplicate & categorize
        print("Stage 3: Deduplicating and categorizing...")
        span = create_span("stage:dedup_categorize", {})
        try:
            all_text = "\n\n".join(
                f"=== {agent['name']} ===\n{raw}"
                for agent, raw in zip(self.agents, raw_failures)
            )
            failures = await self._deduplicate(all_text)
            result.failure_modes = failures
            end_span(span, output=f"{len(failures)} unique failures")
        except Exception:
            end_span(span, error="dedup_categorize failed")
            raise

        # Stage 4: Invert failures → solutions
        print("Stage 4: Inverting failures into solutions...")
        span = create_span("stage:inversion", {"failure_count": len(failures)})
        try:
            solutions = await self._invert(failures)
            result.solutions = solutions
            end_span(span, output=f"{len(solutions)} solutions")
        except Exception:
            end_span(span, error="inversion failed")
            raise

        # Stage 5: Rank by severity × likelihood
        print("Stage 5: Ranking by severity × likelihood...")
        span = create_span("stage:ranking", {"failure_count": len(failures)})
        try:
            await self._rank(failures, solutions)
            end_span(span, output="ranking complete")
        except Exception:
            end_span(span, error="ranking failed")
            raise

        # Sort by composite score descending
        result.failure_modes.sort(key=lambda f: f.composite, reverse=True)

        # Stage 6: Synthesize final output
        print("Stage 6: Synthesizing final briefing...")
        span = create_span("stage:synthesis", {})
        try:
            result.synthesis = await self._synthesize(question, failures, solutions)
            end_span(span, output=f"synthesis {len(result.synthesis)} chars")
        except Exception:
            end_span(span, error="synthesis failed")
            raise

        return result

    async def _generate_failures(self, question: str) -> list[str]:
        """Stage 2: All agents generate failure modes in parallel."""
        prompt = FAILURE_GENERATION_PROMPT.format(question=question)

        async def query_agent(agent: dict) -> str:
            return await agent_complete(
                agent=agent,
                fallback_model=self.thinking_model,
                messages=[{"role": "user", "content": prompt}],
                thinking_budget=self.thinking_budget,
                anthropic_client=self.client,
            )

        _results = await asyncio.gather(
            *(query_agent(agent) for agent in self.agents),
            return_exceptions=True,
        )
        _results = filter_exceptions(_results, label="p06_triz")
        return _results

    async def _deduplicate(self, all_failures: str) -> list[FailureMode]:
        """Stage 3: Deduplicate and categorize failure modes."""
        response = await llm_complete(
            self.client,
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": DEDUPLICATION_PROMPT.format(all_failures=all_failures),
            }],
            agent_name="dedup",
        )
        data = parse_json_array(extract_text(response))
        return [
            FailureMode(
                id=item["id"],
                title=item["title"],
                description=item["description"],
                category=item.get("category", "operational"),
            )
            for item in data
        ]

    async def _invert(self, failures: list[FailureMode]) -> list[Solution]:
        """Stage 4: Invert each failure into a solution."""
        failures_json = json.dumps(
            [{"id": f.id, "title": f.title, "description": f.description, "category": f.category}
             for f in failures],
            indent=2,
        )
        response = await llm_complete(
            self.client,
            model=self.orchestration_model,
            max_tokens=8192,
            messages=[{
                "role": "user",
                "content": INVERSION_PROMPT.format(failures_json=failures_json),
            }],
            agent_name="inversion",
        )
        data = parse_json_array(extract_text(response))
        return [
            Solution(
                failure_id=item["failure_id"],
                title=item["solution_title"],
                description=item["solution_description"],
            )
            for item in data
        ]

    async def _rank(
        self, failures: list[FailureMode], solutions: list[Solution]
    ) -> None:
        """Stage 5: Score severity × likelihood, mutate failure objects."""
        sol_map = {s.failure_id: s for s in solutions}
        combined = json.dumps(
            [
                {
                    "failure_id": f.id,
                    "failure_title": f.title,
                    "failure_description": f.description,
                    "solution_title": sol_map[f.id].title if f.id in sol_map else "",
                    "solution_description": sol_map[f.id].description if f.id in sol_map else "",
                }
                for f in failures
            ],
            indent=2,
        )
        response = await llm_complete(
            self.client,
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": RANKING_PROMPT.format(failures_and_solutions=combined),
            }],
            agent_name="ranking",
        )
        data = parse_json_array(extract_text(response))
        score_map = {item["failure_id"]: item for item in data}
        for f in failures:
            if f.id in score_map:
                s = score_map[f.id]
                f.severity = s.get("severity", 0)
                f.likelihood = s.get("likelihood", 0)
                f.composite = s.get("composite", f.severity * f.likelihood)
                f.rationale = s.get("rationale", "")

    async def _synthesize(
        self,
        question: str,
        failures: list[FailureMode],
        solutions: list[Solution],
    ) -> str:
        """Stage 6: Produce final actionable briefing."""
        sol_map = {s.failure_id: s for s in solutions}
        ranked = json.dumps(
            [
                {
                    "rank": i + 1,
                    "failure": f.title,
                    "category": f.category,
                    "severity": f.severity,
                    "likelihood": f.likelihood,
                    "composite": f.composite,
                    "rationale": f.rationale,
                    "solution": sol_map[f.id].title if f.id in sol_map else "",
                    "solution_detail": sol_map[f.id].description if f.id in sol_map else "",
                }
                for i, f in enumerate(failures)
            ],
            indent=2,
        )
        prompt = SYNTHESIS_PROMPT.format(
            question=question, ranked_results=ranked
        )
        return await self._synth.synthesize(
            protocol_prompt=prompt, question=question
        )


