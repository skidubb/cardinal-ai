"""P38: Klein Pre-Mortem Protocol — Agent-agnostic orchestrator.

Gary Klein's prospective hindsight method: imagine the plan has already
failed, then work backwards to understand how.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field

import anthropic

from .prompts import (
    FAILURE_EXTRACTION_PROMPT,
    FAILURE_NARRATIVE_PROMPT,
    MITIGATION_SYNTHESIS_PROMPT,
)


@dataclass
class PreMortemResult:
    question: str
    time_horizon: str = "18 months"
    narratives: dict[str, str] = field(default_factory=dict)
    failure_modes: list[dict] = field(default_factory=list)
    overlooked_signals: list[str] = field(default_factory=list)
    mitigation_map: str = ""


class PreMortemOrchestrator:
    """Runs the 4-phase Klein Pre-Mortem protocol with any set of agents."""

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

    async def run(self, question: str, time_horizon: str = "18 months") -> PreMortemResult:
        """Execute the full Klein Pre-Mortem protocol."""
        result = PreMortemResult(question=question, time_horizon=time_horizon)

        # Phase 1: Frame (implicit — the prompt frames the pre-mortem)
        # Phase 2: Independent failure narratives (parallel)
        print("Phase 2: Generating independent failure narratives...")
        narratives = await self._generate_narratives(question, time_horizon)
        result.narratives = {
            agent["name"]: narratives[i]
            for i, agent in enumerate(self.agents)
        }

        # Phase 3: Failure mode extraction
        print("Phase 3: Extracting failure modes...")
        all_text = "\n\n".join(
            f"=== {agent['name']} ===\n{narrative}"
            for agent, narrative in zip(self.agents, narratives)
        )
        extraction = await self._extract_failure_modes(all_text)
        result.failure_modes = extraction.get("failure_modes", [])
        result.overlooked_signals = extraction.get("overlooked_signals", [])

        # Phase 4: Mitigation synthesis
        print("Phase 4: Synthesizing mitigation map...")
        # Sort: convergent first, then unique
        sorted_modes = sorted(
            result.failure_modes,
            key=lambda m: (0 if m.get("type") == "convergent" else 1),
        )
        result.mitigation_map = await self._synthesize_mitigations(
            question, time_horizon, sorted_modes, result.overlooked_signals
        )

        return result

    async def _generate_narratives(self, question: str, time_horizon: str) -> list[str]:
        """Phase 2: All agents write failure narratives in parallel."""
        prompt = FAILURE_NARRATIVE_PROMPT.format(
            question=question, time_horizon=time_horizon
        )

        async def query_agent(agent: dict) -> str:
            response = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=self.thinking_budget + 4096,
                thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
                system=agent["system_prompt"],
                messages=[{"role": "user", "content": prompt}],
            )
            return _extract_text(response)

        return await asyncio.gather(
            *(query_agent(agent) for agent in self.agents)
        )

    async def _extract_failure_modes(self, all_narratives: str) -> dict:
        """Phase 3: Extract and classify failure modes using Haiku."""
        response = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": FAILURE_EXTRACTION_PROMPT.format(all_narratives=all_narratives),
            }],
        )
        return _parse_json_object(response.content[0].text)

    async def _synthesize_mitigations(
        self,
        question: str,
        time_horizon: str,
        failure_modes: list[dict],
        overlooked_signals: list[str],
    ) -> str:
        """Phase 4: Produce mitigation map using Opus with extended thinking."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": MITIGATION_SYNTHESIS_PROMPT.format(
                    question=question,
                    time_horizon=time_horizon,
                    failure_modes_json=json.dumps(failure_modes, indent=2),
                    overlooked_signals="\n".join(f"- {s}" for s in overlooked_signals),
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
