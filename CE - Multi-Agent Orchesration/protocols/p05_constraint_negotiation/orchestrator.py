"""P5: Constraint Negotiation Protocol — Agent-agnostic orchestrator.

Agents propose plans with explicit constraints → iteratively revise to satisfy
each other's HARD constraints → synthesis of negotiated outcome.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import anthropic

from .constraints import ConstraintExtractor, ConstraintStore
from .prompts import OPENING_PROMPT, REVISION_PROMPT, SYNTHESIS_PROMPT


@dataclass
class NegotiationArgument:
    name: str
    content: str
    round_number: int


@dataclass
class NegotiationRound:
    round_number: int
    round_type: str  # "opening" or "revision"
    arguments: list[NegotiationArgument] = field(default_factory=list)


@dataclass
class NegotiationResult:
    question: str
    rounds: list[NegotiationRound] = field(default_factory=list)
    constraints: ConstraintStore = field(default_factory=ConstraintStore)
    synthesis: str = ""


class NegotiationOrchestrator:
    """Runs the constraint negotiation protocol with any set of agents."""

    def __init__(
        self,
        agents: list[dict],
        rounds: int = 3,
        thinking_model: str = "claude-opus-4-6",
        orchestration_model: str = "claude-haiku-4-5-20251001",
        thinking_budget: int = 10_000,
    ):
        """
        Args:
            agents: List of {"name": str, "system_prompt": str} dicts.
            rounds: Number of negotiation rounds (minimum 2: opening + revision).
            thinking_model: Model for agent reasoning and synthesis.
            orchestration_model: Model for constraint extraction (Haiku).
            thinking_budget: Token budget for extended thinking on Opus calls.
        """
        if not agents:
            raise ValueError("At least one agent is required")
        if rounds < 2:
            raise ValueError("At least 2 rounds required (opening + revision)")
        self.agents = agents
        self.num_rounds = rounds
        self.thinking_model = thinking_model
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()
        self.constraint_store = ConstraintStore()
        self.extractor = ConstraintExtractor(model=orchestration_model)

    async def run(self, question: str) -> NegotiationResult:
        """Execute the full constraint negotiation protocol."""
        result = NegotiationResult(question=question)

        for round_num in range(1, self.num_rounds + 1):
            if round_num == 1:
                round_type = "opening"
                print(f"Round {round_num}/{self.num_rounds}: Opening proposals...")
            else:
                round_type = "revision"
                print(f"Round {round_num}/{self.num_rounds}: Revisions...")

            arguments = await self._run_round(
                question, round_num, round_type, result.rounds
            )
            result.rounds.append(
                NegotiationRound(
                    round_number=round_num,
                    round_type=round_type,
                    arguments=arguments,
                )
            )

            # Extract constraints after each round
            print(f"  Extracting constraints...")
            extractions = await asyncio.gather(
                *(
                    self.extractor.extract(arg.name, arg.content)
                    for arg in arguments
                )
            )
            for constraints in extractions:
                self.constraint_store.add_many(constraints)

        result.constraints = self.constraint_store

        # Synthesis
        print("Synthesizing negotiation outcome...")
        result.synthesis = await self._synthesize(question, result.rounds)

        return result

    async def _run_round(
        self,
        question: str,
        round_number: int,
        round_type: str,
        prior_rounds: list[NegotiationRound],
    ) -> list[NegotiationArgument]:
        """Run a single negotiation round with all agents in parallel."""

        async def query_agent(agent: dict) -> NegotiationArgument:
            if round_type == "opening":
                prompt = OPENING_PROMPT.format(question=question)
            else:
                prior_text = _format_prior_arguments(prior_rounds)
                peer_constraints = self.constraint_store.format_for_prompt(
                    exclude_role=agent["name"]
                )
                prompt = REVISION_PROMPT.format(
                    question=question,
                    round_number=round_number,
                    peer_constraints=peer_constraints,
                    prior_arguments=prior_text,
                )

            response = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=self.thinking_budget + 4096,
                thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
                system=agent["system_prompt"],
                messages=[{"role": "user", "content": prompt}],
            )
            return NegotiationArgument(
                name=agent["name"],
                content=_extract_text(response),
                round_number=round_number,
            )

        return await asyncio.gather(
            *(query_agent(agent) for agent in self.agents)
        )

    async def _synthesize(
        self, question: str, rounds: list[NegotiationRound]
    ) -> str:
        """Synthesize the full negotiation transcript."""
        transcript = _format_prior_arguments(rounds)
        constraint_table = self.constraint_store.format_for_prompt()
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            system="You are a strategic synthesizer producing actionable conclusions from constraint-based negotiations.",
            messages=[{
                "role": "user",
                "content": SYNTHESIS_PROMPT.format(
                    question=question,
                    constraint_table=constraint_table,
                    transcript=transcript,
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


def _format_prior_arguments(rounds: list[NegotiationRound]) -> str:
    """Format prior negotiation rounds for inclusion in prompts."""
    sections = []
    for rnd in rounds:
        round_label = f"--- Round {rnd.round_number} ({rnd.round_type}) ---"
        args = "\n\n".join(
            f"[{arg.name}]:\n{arg.content}" for arg in rnd.arguments
        )
        sections.append(f"{round_label}\n{args}")
    return "\n\n".join(sections)
