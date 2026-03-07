"""P4: Multi-Round Debate Protocol — Agent-agnostic orchestrator.

N rounds of structured debate → synthesis of evolved positions.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from protocols.langfuse_tracing import trace_protocol, create_span, end_span
from protocols.llm import extract_text, llm_complete, filter_exceptions
from protocols.synthesis import SynthesisEngine

from protocols.scoping import build_context_blocks, filter_context_for_agent, get_primary_scope
from protocols.tracing import make_client
from protocols.config import THINKING_MODEL
from .prompts import (
    FINAL_PROMPT,
    OPENING_PROMPT,
    REBUTTAL_PROMPT,
    SYNTHESIS_PROMPT,
    format_prior_arguments,
)


@dataclass
class DebateArgument:
    name: str
    content: str
    round_number: int
    scope: str = "all"


@dataclass
class DebateRound:
    round_number: int
    round_type: str  # "opening", "rebuttal", "final"
    arguments: list[DebateArgument] = field(default_factory=list)


@dataclass
class DebateResult:
    question: str
    rounds: list[DebateRound] = field(default_factory=list)
    synthesis: str = ""


class DebateOrchestrator:
    """Runs the multi-round debate protocol with any set of agents."""

    def __init__(
        self,
        agents: list[dict],
        rounds: int = 3,
        thinking_model: str = THINKING_MODEL,
        thinking_budget: int = 10_000,
        trace: bool = False,
        trace_path: str | None = None,
        synthesis_engine: SynthesisEngine | None = None,
    ):
        """
        Args:
            agents: List of {"name": str, "system_prompt": str} dicts.
            rounds: Number of debate rounds (minimum 2: opening + final).
            thinking_model: Model for all debate rounds and synthesis.
            thinking_budget: Token budget for extended thinking on Opus calls.
            trace: Enable JSONL execution tracing.
            trace_path: Explicit path for trace file (overrides auto-generated).
            synthesis_engine: Optional SynthesisEngine instance.
        """
        if not agents:
            raise ValueError("At least one agent is required")
        if rounds < 2:
            raise ValueError("At least 2 rounds required (opening + final)")
        self.agents = agents
        self.num_rounds = rounds
        self.thinking_model = thinking_model
        self.thinking_budget = thinking_budget
        self.client = make_client(protocol_id="p04_multi_round_debate", trace=trace, trace_path=Path(trace_path) if trace_path else None)
        self._synth = synthesis_engine or SynthesisEngine(
            self.client, thinking_model, thinking_budget, use_agent=True
        )

    @trace_protocol("p04_multi_round_debate")
    async def run(self, question: str) -> DebateResult:
        """Execute the full multi-round debate protocol."""
        result = DebateResult(question=question)

        for round_num in range(1, self.num_rounds + 1):
            if round_num == 1:
                round_type = "opening"
                print(f"Round {round_num}/{self.num_rounds}: Opening statements...")
            elif round_num == self.num_rounds:
                round_type = "final"
                print(f"Round {round_num}/{self.num_rounds}: Final statements...")
            else:
                round_type = "rebuttal"
                print(f"Round {round_num}/{self.num_rounds}: Rebuttals...")

            span = create_span(f"stage:round_{round_num}_{round_type}", {"round_number": round_num, "round_type": round_type, "agent_count": len(self.agents)})
            try:
                arguments = await self._run_round(
                    question, round_num, round_type, result.rounds
                )
                end_span(span, output=f"{len(arguments)} arguments")
            except Exception:
                end_span(span, error=f"round_{round_num}_{round_type} failed")
                raise
            result.rounds.append(
                DebateRound(
                    round_number=round_num,
                    round_type=round_type,
                    arguments=arguments,
                )
            )

        # Synthesis
        print("Synthesizing debate...")
        span = create_span("stage:synthesis", {"round_count": len(result.rounds)})
        try:
            result.synthesis = await self._synthesize(question, result.rounds)
            end_span(span, output=f"synthesis {len(result.synthesis)} chars")
        except Exception:
            end_span(span, error="synthesis failed")
            raise

        return result

    async def _run_round(
        self,
        question: str,
        round_number: int,
        round_type: str,
        prior_rounds: list[DebateRound],
    ) -> list[DebateArgument]:
        """Run a single debate round with all agents in parallel."""

        async def query_agent(agent: dict) -> DebateArgument:
            if round_type == "opening":
                prompt = OPENING_PROMPT.format(question=question)
            elif round_type == "final":
                context_blocks = build_context_blocks(prior_rounds)
                scoped_args = filter_context_for_agent(agent, context_blocks)
                prompt = FINAL_PROMPT.format(
                    question=question,
                    prior_arguments=scoped_args,
                )
            else:
                context_blocks = build_context_blocks(prior_rounds)
                scoped_args = filter_context_for_agent(agent, context_blocks)
                prompt = REBUTTAL_PROMPT.format(
                    question=question,
                    round_number=round_number,
                    prior_arguments=scoped_args,
                )

            response = await llm_complete(
                self.client,
                model=self.thinking_model,
                max_tokens=self.thinking_budget + 4096,
                thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
                system=agent["system_prompt"],
                messages=[{"role": "user", "content": prompt}],
                agent_name=agent["name"],
            )
            return DebateArgument(
                name=agent["name"],
                content=extract_text(response),
                round_number=round_number,
                scope=get_primary_scope(agent),
            )

        _results = await asyncio.gather(
            *(query_agent(agent) for agent in self.agents),
            return_exceptions=True,
        )
        _results = filter_exceptions(_results, label="p04_multi_round_debate")
        return _results

    async def _synthesize(
        self, question: str, rounds: list[DebateRound]
    ) -> str:
        """Synthesize the full debate transcript."""
        transcript = format_prior_arguments(rounds)
        prompt = SYNTHESIS_PROMPT.format(
            question=question, transcript=transcript
        )
        return await self._synth.synthesize(
            protocol_prompt=prompt,
            question=question,
            system_prompt="You are a strategic synthesizer producing actionable conclusions from structured debates.",
        )




