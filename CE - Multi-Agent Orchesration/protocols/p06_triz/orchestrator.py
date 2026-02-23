"""P6: TRIZ Inversion Protocol — Agent-agnostic orchestrator.

"What would guarantee failure?" → invert failures into solutions.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

import anthropic

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
        thinking_model: str = "claude-opus-4-6",
        orchestration_model: str = "claude-haiku-4-5-20251001",
        thinking_budget: int = 10_000,
    ):
        """
        Args:
            agents: List of {"name": str, "system_prompt": str} dicts.
                    Any agents work — C-Suite, GTM, custom, etc.
            thinking_model: Model for agent reasoning (failure gen, synthesis).
            orchestration_model: Model for mechanical steps (dedup, invert, rank).
            thinking_budget: Token budget for extended thinking on Opus calls.
        """
        if not agents:
            raise ValueError("At least one agent is required")
        self.agents = agents
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    async def run(self, question: str) -> TRIZResult:
        """Execute the full TRIZ Inversion protocol."""
        result = TRIZResult(question=question)

        # Stage 1: Reframe (implicit — the prompt does this)
        # Stage 2: Parallel failure generation
        print("Stage 2: Generating failure modes...")
        raw_failures = await self._generate_failures(question)
        result.agent_contributions = {
            agent["name"]: raw_failures[i]
            for i, agent in enumerate(self.agents)
        }

        # Stage 3: Deduplicate & categorize
        print("Stage 3: Deduplicating and categorizing...")
        all_text = "\n\n".join(
            f"=== {agent['name']} ===\n{raw}"
            for agent, raw in zip(self.agents, raw_failures)
        )
        failures = await self._deduplicate(all_text)
        result.failure_modes = failures

        # Stage 4: Invert failures → solutions
        print("Stage 4: Inverting failures into solutions...")
        solutions = await self._invert(failures)
        result.solutions = solutions

        # Stage 5: Rank by severity × likelihood
        print("Stage 5: Ranking by severity × likelihood...")
        await self._rank(failures, solutions)

        # Sort by composite score descending
        result.failure_modes.sort(key=lambda f: f.composite, reverse=True)

        # Stage 6: Synthesize final output
        print("Stage 6: Synthesizing final briefing...")
        result.synthesis = await self._synthesize(question, failures, solutions)

        return result

    async def _generate_failures(self, question: str) -> list[str]:
        """Stage 2: All agents generate failure modes in parallel."""
        prompt = FAILURE_GENERATION_PROMPT.format(question=question)

        async def query_agent(agent: dict) -> str:
            messages = [{"role": "user", "content": prompt}]
            response = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=self.thinking_budget + 4096,
                thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
                system=agent["system_prompt"],
                messages=messages,
            )
            return _extract_text(response)

        return await asyncio.gather(
            *(query_agent(agent) for agent in self.agents)
        )

    async def _deduplicate(self, all_failures: str) -> list[FailureMode]:
        """Stage 3: Deduplicate and categorize failure modes."""
        response = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": DEDUPLICATION_PROMPT.format(all_failures=all_failures),
            }],
        )
        data = _parse_json_array(response.content[0].text)
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
        response = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": INVERSION_PROMPT.format(failures_json=failures_json),
            }],
        )
        data = _parse_json_array(response.content[0].text)
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
        response = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": RANKING_PROMPT.format(failures_and_solutions=combined),
            }],
        )
        data = _parse_json_array(response.content[0].text)
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
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": SYNTHESIS_PROMPT.format(
                    question=question, ranked_results=ranked
                ),
            }],
        )
        return _extract_text(response)


def _extract_text(response: anthropic.types.Message) -> str:
    """Extract text from a response that may contain thinking blocks."""
    parts = []
    for block in response.content:
        if hasattr(block, "text"):
            parts.append(block.text)
    return "\n".join(parts)


def _parse_json_array(text: str) -> list[dict]:
    """Extract a JSON array from LLM output that may contain markdown fences."""
    text = text.strip()
    # Try to find JSON array between markdown fences
    if "```" in text:
        import re
        match = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
    # Fallback: find the first [ ... ] in the text
    if not text.startswith("["):
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            text = text[start:end + 1]
    return json.loads(text)
