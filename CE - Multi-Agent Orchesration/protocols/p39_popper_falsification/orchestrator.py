"""P39: Popper Falsification Gate — Agent-agnostic orchestrator.

Post-protocol quality gate: test a recommendation by actively searching
for evidence that it is WRONG.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field

import anthropic

from .prompts import (
    EVIDENCE_SEARCH_PROMPT,
    GENERATE_CONDITIONS_PROMPT,
    VERDICT_PROMPT,
)


@dataclass
class FalsificationResult:
    recommendation: str
    conditions: list[dict] = field(default_factory=list)
    verdict: str = ""
    verdict_reasoning: str = ""
    synthesis: str = ""


class FalsificationOrchestrator:
    """Runs the 3-phase Popper Falsification Gate with any set of agents."""

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

    async def run(self, recommendation: str, question: str = "") -> FalsificationResult:
        """Execute the full Popper Falsification Gate."""
        result = FalsificationResult(recommendation=recommendation)
        context = question or "No additional context provided."

        # Phase 1: Generate falsification conditions
        print("Phase 1: Generating falsification conditions...")
        conditions = await self._generate_conditions(recommendation, context)
        result.conditions = [{"condition": c} for c in conditions]

        # Phase 2: Active evidence search (parallel across agents × conditions)
        print("Phase 2: Searching for disconfirming evidence...")
        await self._search_evidence(recommendation, context, result.conditions)

        # Phase 3: Verdict
        print("Phase 3: Rendering verdict...")
        await self._render_verdict(recommendation, result)

        return result

    async def _generate_conditions(self, recommendation: str, context: str) -> list[str]:
        """Phase 1: Agents generate falsification conditions in parallel."""
        prompt = GENERATE_CONDITIONS_PROMPT.format(
            recommendation=recommendation, context=context
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

        raw_outputs = await asyncio.gather(
            *(query_agent(agent) for agent in self.agents)
        )

        # Combine all agent outputs and deduplicate via orchestration model
        combined = "\n\n".join(
            f"=== {agent['name']} ===\n{output}"
            for agent, output in zip(self.agents, raw_outputs)
        )
        response = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": (
                    "Below are falsification conditions from multiple analysts. "
                    "Merge duplicates and return a JSON array of 3-5 unique condition "
                    "strings, each a single sentence.\n\n" + combined
                ),
            }],
        )
        return _parse_json_array(response.content[0].text)

    async def _search_evidence(
        self, recommendation: str, context: str, conditions: list[dict]
    ) -> None:
        """Phase 2: For each condition, agents search for disconfirming evidence."""

        async def search_condition(condition_dict: dict) -> None:
            condition = condition_dict["condition"]
            prompt = EVIDENCE_SEARCH_PROMPT.format(
                recommendation=recommendation,
                condition=condition,
                context=context,
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

            results = await asyncio.gather(
                *(query_agent(agent) for agent in self.agents)
            )
            condition_dict["evidence_for"] = []
            condition_dict["evidence_against"] = []
            condition_dict["assessment"] = ""
            condition_dict["agent_analyses"] = {
                agent["name"]: result
                for agent, result in zip(self.agents, results)
            }

        await asyncio.gather(*(search_condition(c) for c in conditions))

    async def _render_verdict(
        self, recommendation: str, result: FalsificationResult
    ) -> None:
        """Phase 3: Judge renders verdict using orchestration model."""
        conditions_evidence = json.dumps(
            [
                {
                    "condition": c["condition"],
                    "agent_analyses": c.get("agent_analyses", {}),
                }
                for c in result.conditions
            ],
            indent=2,
        )
        response = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": VERDICT_PROMPT.format(
                    recommendation=recommendation,
                    conditions_evidence=conditions_evidence,
                ),
            }],
        )
        data = _parse_json_object(response.content[0].text)

        # Update conditions with verdict info
        for verdict_cond in data.get("conditions", []):
            for cond in result.conditions:
                if cond["condition"] == verdict_cond.get("condition"):
                    cond["activated"] = verdict_cond.get("activated", False)
                    cond["reasoning"] = verdict_cond.get("reasoning", "")
                    break

        result.verdict = data.get("verdict", "UNKNOWN")
        result.verdict_reasoning = data.get("verdict_reasoning", "")
        result.synthesis = data.get("synthesis", "")


def _extract_text(response: anthropic.types.Message) -> str:
    """Extract text from a response that may contain thinking blocks."""
    parts = []
    for block in response.content:
        if hasattr(block, "text"):
            parts.append(block.text)
    return "\n".join(parts)


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
