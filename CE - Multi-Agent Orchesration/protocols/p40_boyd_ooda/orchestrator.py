"""P40: Boyd OODA Rapid Cycle Protocol — Agent-agnostic orchestrator.

Speed over quality. Complete the loop FASTER, not better.
The advantage goes to whoever cycles through Observe-Orient-Decide-Act fastest.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

import anthropic

from .prompts import (
    ACT_PROMPT,
    DECIDE_PROMPT,
    OBSERVE_PROMPT,
    ORIENT_PROMPT,
    SYNTHESIS_PROMPT,
)


@dataclass
class OODAResult:
    question: str
    cycles: list[dict] = field(default_factory=list)
    final_action: str = ""
    synthesis: str = ""


class OODAOrchestrator:
    """Runs the Boyd OODA Rapid Cycle protocol with any set of agents."""

    def __init__(
        self,
        agents: list[dict],
        thinking_model: str = "claude-opus-4-6",
        orchestration_model: str = "claude-haiku-4-5-20251001",
        thinking_budget: int = 10_000,
        num_cycles: int = 2,
    ):
        """
        Args:
            agents: List of {"name": str, "system_prompt": str} dicts.
            thinking_model: Model for agent reasoning (orient, synthesis).
            orchestration_model: Model for compact phases (observe, decide).
            thinking_budget: Token budget for extended thinking on Opus calls.
            num_cycles: Number of OODA loops to run.
        """
        if not agents:
            raise ValueError("At least one agent is required")
        self.agents = agents
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.num_cycles = num_cycles
        self.client = anthropic.AsyncAnthropic()

    async def run(self, question: str) -> OODAResult:
        """Execute the full Boyd OODA Rapid Cycle protocol."""
        result = OODAResult(question=question)
        prior_context = ""

        for cycle_num in range(1, self.num_cycles + 1):
            print(f"\n--- OODA Cycle {cycle_num}/{self.num_cycles} ---")
            cycle = {"cycle_number": cycle_num}

            # Phase 1: OBSERVE (parallel across agents, compact)
            print(f"  Observe...")
            observations = await self._observe(question, prior_context)
            cycle["observe"] = observations

            # Phase 2: ORIENT (thinking-enabled, the critical step)
            print(f"  Orient...")
            model = await self._orient(observations)
            cycle["orient"] = model

            # Phase 3: DECIDE (compact)
            print(f"  Decide...")
            decision = await self._decide(model)
            cycle["decide"] = decision

            # Phase 4: ACT (project consequences for next cycle)
            print(f"  Act...")
            act_output = await self._act(decision, question)
            cycle["act"] = act_output

            result.cycles.append(cycle)

            # Set up context for next cycle's Observe phase
            prior_context = (
                f"\n\nPRIOR CYCLE ACTION AND CONSEQUENCES:\n"
                f"Decision taken: {decision}\n"
                f"Projected consequences: {act_output}"
            )

        result.final_action = result.cycles[-1]["decide"]

        # Synthesis across all cycles
        print(f"\nSynthesizing across {self.num_cycles} cycles...")
        result.synthesis = await self._synthesize(question, result.cycles)

        return result

    async def _observe(self, question: str, prior_context: str) -> str:
        """Phase 1: Parallel observation across agents, compact thinking."""
        prompt = OBSERVE_PROMPT.format(question=question, prior_context=prior_context)
        compact_budget = 3000

        async def query_agent(agent: dict) -> str:
            response = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=compact_budget + 2048,
                thinking={"type": "enabled", "budget_tokens": compact_budget},
                system=agent["system_prompt"],
                messages=[{"role": "user", "content": prompt}],
            )
            return f"=== {agent['name']} ===\n{_extract_text(response)}"

        results = await asyncio.gather(
            *(query_agent(agent) for agent in self.agents)
        )
        return "\n\n".join(results)

    async def _orient(self, observations: str) -> str:
        """Phase 2: Orient — update mental model. Thinking-enabled."""
        prompt = ORIENT_PROMPT.format(observations=observations)
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{"role": "user", "content": prompt}],
        )
        return _extract_text(response)

    async def _decide(self, model: str) -> str:
        """Phase 3: Decide — single best immediate action. Compact."""
        prompt = DECIDE_PROMPT.format(model=model)
        compact_budget = 3000
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=compact_budget + 2048,
            thinking={"type": "enabled", "budget_tokens": compact_budget},
            messages=[{"role": "user", "content": prompt}],
        )
        return _extract_text(response)

    async def _act(self, decision: str, question: str) -> str:
        """Phase 4: Act — project consequences for next cycle."""
        prompt = ACT_PROMPT.format(decision=decision, question=question)
        compact_budget = 3000
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=compact_budget + 2048,
            thinking={"type": "enabled", "budget_tokens": compact_budget},
            messages=[{"role": "user", "content": prompt}],
        )
        return _extract_text(response)

    async def _synthesize(self, question: str, cycles: list[dict]) -> str:
        """Final synthesis across all OODA cycles."""
        cycles_json = json.dumps(cycles, indent=2)
        prompt = SYNTHESIS_PROMPT.format(
            num_cycles=len(cycles),
            question=question,
            cycles_json=cycles_json,
        )
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{"role": "user", "content": prompt}],
        )
        return _extract_text(response)


def _extract_text(response: anthropic.types.Message) -> str:
    """Extract text from a response that may contain thinking blocks."""
    parts = []
    for block in response.content:
        if hasattr(block, "text"):
            parts.append(block.text)
    return "\n".join(parts)
