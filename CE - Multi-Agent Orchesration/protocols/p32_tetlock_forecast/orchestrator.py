"""P32: Tetlock Calibrated Forecast Protocol — Agent-agnostic orchestrator.

4-step sequential pipeline: Fermi Decomposition -> Base Rate Establishment ->
Inside-View Adjustment -> Extremizing Aggregation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import anthropic

from .prompts import (
    BASE_RATE_PROMPT,
    EXTREMIZING_AGGREGATION_PROMPT,
    FERMI_DECOMPOSITION_PROMPT,
    INSIDE_VIEW_ADJUSTMENT_PROMPT,
    SYNTHESIS_PROMPT,
)


@dataclass
class ForecastResult:
    question: str
    decomposition: str = ""
    base_rates: str = ""
    adjustments: str = ""
    final_probability: str = ""
    synthesis: str = ""


class TetlockOrchestrator:
    """Runs the 4-step Tetlock Calibrated Forecast protocol with any set of agents."""

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
                    Each agent handles one step of the sequential pipeline.
            thinking_model: Model for all forecast reasoning steps.
            orchestration_model: Model for mechanical steps (unused in this protocol).
            thinking_budget: Token budget for extended thinking on Opus calls.
        """
        if not agents:
            raise ValueError("At least one agent is required")
        self.agents = agents
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    async def run(self, question: str) -> ForecastResult:
        """Execute the full Tetlock Calibrated Forecast protocol."""
        result = ForecastResult(question=question)

        # Step 1: Fermi Decomposition
        agent_1 = self.agents[0 % len(self.agents)]
        print(f"Step 1: Fermi Decomposition ({agent_1['name']})...")
        result.decomposition = await self._fermi_decomposition(question, agent_1)

        # Step 2: Base Rate Establishment
        agent_2 = self.agents[1 % len(self.agents)]
        print(f"Step 2: Base Rate Establishment ({agent_2['name']})...")
        result.base_rates = await self._base_rate_establishment(question, result.decomposition, agent_2)

        # Step 3: Inside-View Adjustment
        agent_3 = self.agents[2 % len(self.agents)]
        print(f"Step 3: Inside-View Adjustment ({agent_3['name']})...")
        result.adjustments = await self._inside_view_adjustment(question, result.base_rates, agent_3)

        # Step 4: Extremizing Aggregation
        agent_4 = self.agents[3 % len(self.agents)]
        print(f"Step 4: Extremizing Aggregation ({agent_4['name']})...")
        result.final_probability = await self._extremizing_aggregation(question, result.adjustments, agent_4)

        # Synthesis
        print("Synthesizing final forecast...")
        result.synthesis = await self._synthesize(result)

        return result

    async def _fermi_decomposition(self, question: str, agent: dict) -> str:
        """Step 1: Break question into independently estimable sub-questions."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            system=agent["system_prompt"],
            messages=[{
                "role": "user",
                "content": FERMI_DECOMPOSITION_PROMPT.format(question=question),
            }],
        )
        return _extract_text(response)

    async def _base_rate_establishment(self, question: str, decomposition: str, agent: dict) -> str:
        """Step 2: Establish outside-view base rates for each sub-question."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            system=agent["system_prompt"],
            messages=[{
                "role": "user",
                "content": BASE_RATE_PROMPT.format(
                    question=question, decomposition=decomposition
                ),
            }],
        )
        return _extract_text(response)

    async def _inside_view_adjustment(self, question: str, base_rates: str, agent: dict) -> str:
        """Step 3: Adjust base rates with case-specific inside-view factors."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            system=agent["system_prompt"],
            messages=[{
                "role": "user",
                "content": INSIDE_VIEW_ADJUSTMENT_PROMPT.format(
                    question=question, base_rates=base_rates
                ),
            }],
        )
        return _extract_text(response)

    async def _extremizing_aggregation(self, question: str, adjustments: str, agent: dict) -> str:
        """Step 4: Apply extremizing formula and produce final probability."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            system=agent["system_prompt"],
            messages=[{
                "role": "user",
                "content": EXTREMIZING_AGGREGATION_PROMPT.format(
                    question=question, adjustments=adjustments
                ),
            }],
        )
        return _extract_text(response)

    async def _synthesize(self, result: ForecastResult) -> str:
        """Produce final human-readable forecast summary."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": SYNTHESIS_PROMPT.format(
                    question=result.question,
                    decomposition=result.decomposition,
                    base_rates=result.base_rates,
                    adjustments=result.adjustments,
                    final_probability=result.final_probability,
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
    import json
    return json.loads(text)
