"""P32: Tetlock Calibrated Forecast Protocol — Agent-agnostic orchestrator.

4-step sequential pipeline: Fermi Decomposition -> Base Rate Establishment ->
Inside-View Adjustment -> Extremizing Aggregation.
"""

from __future__ import annotations

from dataclasses import dataclass

import anthropic
from protocols.langfuse_tracing import trace_protocol
from protocols.llm import extract_text

from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
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
        thinking_model: str = THINKING_MODEL,
        orchestration_model: str = ORCHESTRATION_MODEL,
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

    @trace_protocol("p32_tetlock_forecast")
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
        return extract_text(response)

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
        return extract_text(response)

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
        return extract_text(response)

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
        return extract_text(response)

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
        return extract_text(response)




