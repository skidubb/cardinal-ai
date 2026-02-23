"""P31: Wittgenstein Language Game Protocol — Agent-agnostic orchestrator.

Reframe problems in radically different vocabularies to find where they become tractable.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

import anthropic

from .prompts import (
    RANKING_PROMPT,
    REFRAME_PROMPT,
    SYNTHESIS_PROMPT,
    VOCABULARY_ASSIGNMENT_PROMPT,
)


@dataclass
class LanguageGameResult:
    question: str
    vocabulary_assignments: dict[str, str] = field(default_factory=dict)
    reframings: dict[str, str] = field(default_factory=dict)
    ranking: str = ""
    best_reframe: str = ""
    synthesis: str = ""


class LanguageGameOrchestrator:
    """Runs the Wittgenstein Language Game protocol with any set of agents."""

    def __init__(
        self,
        agents: list[dict],
        thinking_model: str = "claude-opus-4-6",
        orchestration_model: str = "claude-haiku-4-5-20251001",
        thinking_budget: int = 10_000,
    ):
        if not agents:
            raise ValueError("At least one agent is required")
        self.agents = agents
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    async def run(self, question: str) -> LanguageGameResult:
        """Execute the full Wittgenstein Language Game protocol."""
        result = LanguageGameResult(question=question)

        # Phase 1: Assign vocabularies
        print("Phase 1: Assigning vocabularies...")
        assignments = await self._assign_vocabularies(question)
        result.vocabulary_assignments = assignments

        # Phase 2: Parallel reframing
        print("Phase 2: Reframing in assigned vocabularies...")
        reframings = await self._reframe(question, assignments)
        result.reframings = reframings

        # Phase 3: Identify tractable framing
        print("Phase 3: Ranking reframings by revelation value...")
        ranking = await self._rank_reframings(question, reframings)
        result.ranking = ranking

        # Phase 4: Synthesize
        print("Phase 4: Synthesizing insights...")
        result.synthesis = await self._synthesize(question, assignments, reframings, ranking)

        return result

    async def _assign_vocabularies(self, question: str) -> dict[str, str]:
        """Phase 1: Assign each agent a domain vocabulary."""
        agent_names = ", ".join(a["name"] for a in self.agents)
        response = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": VOCABULARY_ASSIGNMENT_PROMPT.format(
                    question=question,
                    num_agents=len(self.agents),
                    agent_names=agent_names,
                ),
            }],
        )
        data = _parse_json_object(response.content[0].text)
        # Extract just domain strings
        assignments = {}
        for agent in self.agents:
            if agent["name"] in data:
                val = data[agent["name"]]
                if isinstance(val, dict):
                    assignments[agent["name"]] = val.get("domain", str(val))
                else:
                    assignments[agent["name"]] = str(val)
            else:
                # Fallback: assign in order
                assignments[agent["name"]] = "general systems theory"
        return assignments

    async def _reframe(self, question: str, assignments: dict[str, str]) -> dict[str, str]:
        """Phase 2: Each agent reframes the problem in their assigned vocabulary."""

        async def reframe_agent(agent: dict) -> tuple[str, str]:
            domain = assignments.get(agent["name"], "general systems theory")
            prompt = REFRAME_PROMPT.format(domain=domain, question=question)
            response = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=self.thinking_budget + 4096,
                thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
                system=agent["system_prompt"],
                messages=[{"role": "user", "content": prompt}],
            )
            return agent["name"], _extract_text(response)

        results = await asyncio.gather(
            *(reframe_agent(agent) for agent in self.agents)
        )
        return dict(results)

    async def _rank_reframings(self, question: str, reframings: dict[str, str]) -> str:
        """Phase 3: Rank reframings by revelation value and identify best."""
        reframings_text = "\n\n".join(
            f"=== {name} ===\n{text}" for name, text in reframings.items()
        )
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": RANKING_PROMPT.format(
                    question=question,
                    reframings=reframings_text,
                ),
            }],
        )
        return _extract_text(response)

    async def _synthesize(
        self,
        question: str,
        assignments: dict[str, str],
        reframings: dict[str, str],
        ranking: str,
    ) -> str:
        """Phase 4: Produce final synthesis."""
        assignments_text = "\n".join(
            f"- {name}: {domain}" for name, domain in assignments.items()
        )
        reframings_text = "\n\n".join(
            f"=== {name} ===\n{text}" for name, text in reframings.items()
        )
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": SYNTHESIS_PROMPT.format(
                    question=question,
                    assignments=assignments_text,
                    reframings=reframings_text,
                    ranking=ranking,
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


def _parse_json_object(text: str) -> dict:
    """Extract a JSON object from LLM output that may contain markdown fences."""
    import re
    text = text.strip()
    if "```" in text:
        match = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end + 1]
    return json.loads(text)
