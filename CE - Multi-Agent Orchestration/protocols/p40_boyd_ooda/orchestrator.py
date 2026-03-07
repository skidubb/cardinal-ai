"""P40: Boyd OODA Rapid Cycle Protocol — Agent-agnostic orchestrator.

Speed over quality. Complete the loop FASTER, not better.
The advantage goes to whoever cycles through Observe-Orient-Decide-Act fastest.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

import anthropic
from protocols.langfuse_tracing import trace_protocol, create_span, end_span
from protocols.llm import extract_text, llm_complete, filter_exceptions

from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
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
        thinking_model: str = THINKING_MODEL,
        orchestration_model: str = ORCHESTRATION_MODEL,
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

    @trace_protocol("p40_boyd_ooda")
    async def run(self, question: str) -> OODAResult:
        """Execute the full Boyd OODA Rapid Cycle protocol."""
        result = OODAResult(question=question)
        prior_context = ""

        for cycle_num in range(1, self.num_cycles + 1):
            print(f"\n--- OODA Cycle {cycle_num}/{self.num_cycles} ---")
            cycle = {"cycle_number": cycle_num}

            # Phase 1: OBSERVE (parallel across agents, compact)
            print("  Observe...")
            span = create_span("stage:observe", {"cycle": cycle_num, "agent_count": len(self.agents)})
            try:
                observations = await self._observe(question, prior_context)
                cycle["observe"] = observations
                end_span(span, output=f"cycle {cycle_num} observations collected")
            except Exception:
                end_span(span, error="observe failed")
                raise

            # Phase 2: ORIENT (thinking-enabled, the critical step)
            print("  Orient...")
            span = create_span("stage:orient", {"cycle": cycle_num})
            try:
                model = await self._orient(observations)
                cycle["orient"] = model
                end_span(span, output=f"cycle {cycle_num} mental model updated")
            except Exception:
                end_span(span, error="orient failed")
                raise

            # Phase 3: DECIDE (compact)
            print("  Decide...")
            span = create_span("stage:decide", {"cycle": cycle_num})
            try:
                decision = await self._decide(model)
                cycle["decide"] = decision
                end_span(span, output=f"cycle {cycle_num} decision made")
            except Exception:
                end_span(span, error="decide failed")
                raise

            # Phase 4: ACT (project consequences for next cycle)
            print("  Act...")
            span = create_span("stage:act", {"cycle": cycle_num})
            try:
                act_output = await self._act(decision, question)
                cycle["act"] = act_output
                end_span(span, output=f"cycle {cycle_num} consequences projected")
            except Exception:
                end_span(span, error="act failed")
                raise

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
        span = create_span("stage:synthesis", {"num_cycles": self.num_cycles})
        try:
            result.synthesis = await self._synthesize(question, result.cycles)
            end_span(span, output="synthesis complete")
        except Exception:
            end_span(span, error="synthesis failed")
            raise

        return result

    async def _observe(self, question: str, prior_context: str) -> str:
        """Phase 1: Parallel observation across agents, compact thinking."""
        prompt = OBSERVE_PROMPT.format(question=question, prior_context=prior_context)
        compact_budget = 3000

        async def query_agent(agent: dict) -> str:
            response = await llm_complete(
                self.client,
                model=self.thinking_model,
                max_tokens=compact_budget + 2048,
                thinking={"type": "enabled", "budget_tokens": compact_budget},
                system=agent["system_prompt"],
                messages=[{"role": "user", "content": prompt}],
                agent_name=agent.get("name"),
            )
            return f"=== {agent['name']} ===\n{extract_text(response)}"

        results = await asyncio.gather(
            *(query_agent(agent) for agent in self.agents),
            return_exceptions=True,
        )
        results = filter_exceptions(results, label="p40_boyd_ooda")
        return "\n\n".join(results)

    async def _orient(self, observations: str) -> str:
        """Phase 2: Orient — update mental model. Thinking-enabled."""
        prompt = ORIENT_PROMPT.format(observations=observations)
        response = await llm_complete(
            self.client,
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{"role": "user", "content": prompt}],
            agent_name="orient",
        )
        return extract_text(response)

    async def _decide(self, model: str) -> str:
        """Phase 3: Decide — single best immediate action. Compact."""
        prompt = DECIDE_PROMPT.format(model=model)
        compact_budget = 3000
        response = await llm_complete(
            self.client,
            model=self.thinking_model,
            max_tokens=compact_budget + 2048,
            thinking={"type": "enabled", "budget_tokens": compact_budget},
            messages=[{"role": "user", "content": prompt}],
            agent_name="decide",
        )
        return extract_text(response)

    async def _act(self, decision: str, question: str) -> str:
        """Phase 4: Act — project consequences for next cycle."""
        prompt = ACT_PROMPT.format(decision=decision, question=question)
        compact_budget = 3000
        response = await llm_complete(
            self.client,
            model=self.thinking_model,
            max_tokens=compact_budget + 2048,
            thinking={"type": "enabled", "budget_tokens": compact_budget},
            messages=[{"role": "user", "content": prompt}],
            agent_name="act",
        )
        return extract_text(response)

    async def _synthesize(self, question: str, cycles: list[dict]) -> str:
        """Final synthesis across all OODA cycles."""
        cycles_json = json.dumps(cycles, indent=2)
        prompt = SYNTHESIS_PROMPT.format(
            num_cycles=len(cycles),
            question=question,
            cycles_json=cycles_json,
        )
        response = await llm_complete(
            self.client,
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{"role": "user", "content": prompt}],
            agent_name="synthesis",
        )
        return extract_text(response)


