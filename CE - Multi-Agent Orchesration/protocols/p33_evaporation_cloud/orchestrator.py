"""P33: Goldratt Evaporation Cloud Protocol — Agent-agnostic orchestrator.

Dissolves contradictions by mapping a conflict cloud, surfacing hidden
assumptions behind each logical link, and finding the weakest assumption
whose removal dissolves the entire conflict without compromise.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field

import anthropic

from .prompts import (
    ASSUMPTION_PROMPT,
    CONFLICT_ASSUMPTION_PROMPT,
    INJECTION_PROMPT,
    MAP_CLOUD_PROMPT,
)


@dataclass
class EvaporationCloudResult:
    question: str
    cloud: dict = field(default_factory=dict)
    assumptions: dict[str, list[str]] = field(default_factory=dict)
    injection_point: str = ""
    solution: str = ""
    synthesis: str = ""


class EvaporationCloudOrchestrator:
    """Runs the 3-phase Evaporation Cloud protocol with any set of agents."""

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
            thinking_model: Model for reasoning phases (cloud mapping, injection).
            orchestration_model: Model for mechanical steps.
            thinking_budget: Token budget for extended thinking on Opus calls.
        """
        if not agents:
            raise ValueError("At least one agent is required")
        self.agents = agents
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    async def run(self, question: str) -> EvaporationCloudResult:
        """Execute the full Evaporation Cloud protocol."""
        result = EvaporationCloudResult(question=question)

        # Phase 1: Map the Cloud
        print("Phase 1: Mapping the conflict cloud...")
        result.cloud = await self._map_cloud(question)

        # Phase 2: Attack Assumptions Behind Each Arrow
        print("Phase 2: Surfacing hidden assumptions (5 arrows in parallel)...")
        result.assumptions = await self._attack_assumptions(result.cloud)

        # Phase 3: Identify Injection Point
        print("Phase 3: Identifying injection point...")
        injection = await self._find_injection(result.cloud, result.assumptions)
        result.injection_point = injection["injection_point"]
        result.solution = injection["solution"]
        result.synthesis = injection["synthesis"]

        return result

    async def _map_cloud(self, question: str) -> dict:
        """Phase 1: Structure the conflict as an Evaporation Cloud."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": MAP_CLOUD_PROMPT.format(question=question),
            }],
        )
        text = _extract_text(response)
        return _parse_json_object(text)

    async def _attack_assumptions(self, cloud: dict) -> dict[str, list[str]]:
        """Phase 2: Generate hidden assumptions for all 5 arrows in parallel."""
        arrows = [
            ("Objective → Requirement A", cloud["objective"], cloud["requirement_a"]),
            ("Objective → Requirement B", cloud["objective"], cloud["requirement_b"]),
            ("Requirement A → Prerequisite A", cloud["requirement_a"], cloud["prerequisite_a"]),
            ("Requirement B → Prerequisite B", cloud["requirement_b"], cloud["prerequisite_b"]),
        ]

        async def query_arrow(arrow_label: str, arrow_from: str, arrow_to: str) -> tuple[str, list[str]]:
            prompt = ASSUMPTION_PROMPT.format(
                objective=cloud["objective"],
                requirement_a=cloud["requirement_a"],
                requirement_b=cloud["requirement_b"],
                prerequisite_a=cloud["prerequisite_a"],
                prerequisite_b=cloud["prerequisite_b"],
                arrow_label=arrow_label,
                arrow_from=arrow_from,
                arrow_to=arrow_to,
            )
            response = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=self.thinking_budget + 4096,
                thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
                messages=[{"role": "user", "content": prompt}],
            )
            text = _extract_text(response)
            return arrow_label, _parse_json_array(text)

        async def query_conflict() -> tuple[str, list[str]]:
            prompt = CONFLICT_ASSUMPTION_PROMPT.format(
                objective=cloud["objective"],
                requirement_a=cloud["requirement_a"],
                requirement_b=cloud["requirement_b"],
                prerequisite_a=cloud["prerequisite_a"],
                prerequisite_b=cloud["prerequisite_b"],
            )
            response = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=self.thinking_budget + 4096,
                thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
                messages=[{"role": "user", "content": prompt}],
            )
            text = _extract_text(response)
            return "Prerequisite A ↔ Prerequisite B (conflict)", _parse_json_array(text)

        tasks = [query_arrow(*a) for a in arrows] + [query_conflict()]
        results = await asyncio.gather(*tasks)
        return {label: assumptions for label, assumptions in results}

    async def _find_injection(
        self, cloud: dict, assumptions: dict[str, list[str]]
    ) -> dict:
        """Phase 3: Identify the weakest assumption and the resulting solution."""
        assumptions_text = ""
        for arrow, items in assumptions.items():
            assumptions_text += f"\n**{arrow}:**\n"
            for i, a in enumerate(items, 1):
                assumptions_text += f"  {i}. {a}\n"

        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": INJECTION_PROMPT.format(
                    objective=cloud["objective"],
                    requirement_a=cloud["requirement_a"],
                    requirement_b=cloud["requirement_b"],
                    prerequisite_a=cloud["prerequisite_a"],
                    prerequisite_b=cloud["prerequisite_b"],
                    assumptions_text=assumptions_text,
                ),
            }],
        )
        text = _extract_text(response)
        return _parse_json_object(text)


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


def _parse_json_array(text: str) -> list:
    """Extract a JSON array from LLM output that may contain markdown fences."""
    text = text.strip()
    if "```" in text:
        match = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
    if not text.startswith("["):
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            text = text[start:end + 1]
    return json.loads(text)
