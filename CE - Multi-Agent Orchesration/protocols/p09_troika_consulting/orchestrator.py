"""P9: Troika Consulting — Rotating client/consultant advisory orchestrator."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import anthropic

from .prompts import (
    CLIENT_PRESENT_PROMPT,
    CLIENT_REFLECT_PROMPT,
    CONSULTANT_CONSOLIDATE_PROMPT,
    CONSULTANT_INITIAL_PROMPT,
    CONSULTANT_RESPOND_PROMPT,
    FINAL_SYNTHESIS_PROMPT,
)


@dataclass
class AgentSpec:
    """Minimal agent definition — name + system prompt."""
    name: str
    system_prompt: str


@dataclass
class TroikaRound:
    """Result from a single Troika Consulting round."""
    client_name: str
    consultants: list[str]
    problem_statement: str
    consultant1_response: str
    consultant2_response: str
    consolidated_advice: str
    client_reflection: str
    elapsed_seconds: float = 0.0


@dataclass
class TroikaResult:
    """Complete result from a Troika Consulting run."""
    question: str
    rounds: list[TroikaRound] = field(default_factory=list)
    final_synthesis: str = ""
    elapsed_seconds: float = 0.0
    model_calls: dict[str, int] = field(default_factory=dict)
    timings: dict[str, float] = field(default_factory=dict)


def _extract_text(response) -> str:
    """Pull plain text from an Anthropic API response."""
    for block in response.content:
        if block.type == "text":
            return block.text
    return ""


class TroikaOrchestrator:
    """Runs the Troika Consulting protocol with rotating client/consultant roles."""

    def __init__(
        self,
        agents: list[AgentSpec],
        thinking_model: str = "claude-opus-4-6",
        orchestration_model: str = "claude-haiku-4-5-20251001",
        thinking_budget: int = 10_000,
    ):
        if len(agents) < 3:
            raise ValueError("Troika Consulting requires at least 3 agents.")
        self.agents = agents
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _client_present(self, agent: AgentSpec, question: str) -> str:
        """Phase 1: Client presents the problem (Opus, extended thinking)."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=16_000,
            thinking={
                "type": "enabled",
                "budget_tokens": self.thinking_budget,
            },
            system=agent.system_prompt,
            messages=[
                {"role": "user", "content": CLIENT_PRESENT_PROMPT.format(
                    role_description=agent.system_prompt,
                    question=question,
                )},
            ],
        )
        return _extract_text(response)

    async def _consultant_initial(
        self, consultant: AgentSpec, question: str,
        client_name: str, problem_statement: str,
    ) -> str:
        """Phase 2a: First consultant gives initial analysis (Haiku)."""
        response = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=8_000,
            system=consultant.system_prompt,
            messages=[
                {"role": "user", "content": CONSULTANT_INITIAL_PROMPT.format(
                    role_description=consultant.system_prompt,
                    question=question,
                    client_name=client_name,
                    problem_statement=problem_statement,
                )},
            ],
        )
        return _extract_text(response)

    async def _consultant_respond(
        self, consultant: AgentSpec, question: str,
        client_name: str, problem_statement: str,
        consultant1_name: str, consultant1_response: str,
    ) -> str:
        """Phase 2b: Second consultant responds and builds (Haiku)."""
        response = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=8_000,
            system=consultant.system_prompt,
            messages=[
                {"role": "user", "content": CONSULTANT_RESPOND_PROMPT.format(
                    role_description=consultant.system_prompt,
                    question=question,
                    client_name=client_name,
                    problem_statement=problem_statement,
                    consultant1_name=consultant1_name,
                    consultant1_response=consultant1_response,
                )},
            ],
        )
        return _extract_text(response)

    async def _consolidate(
        self, question: str, client_name: str, problem_statement: str,
        consultant1_name: str, consultant1_response: str,
        consultant2_name: str, consultant2_response: str,
    ) -> str:
        """Phase 2c: Consolidate consultation into clear advice (Haiku)."""
        response = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=8_000,
            messages=[
                {"role": "user", "content": CONSULTANT_CONSOLIDATE_PROMPT.format(
                    question=question,
                    client_name=client_name,
                    problem_statement=problem_statement,
                    consultant1_name=consultant1_name,
                    consultant1_response=consultant1_response,
                    consultant2_name=consultant2_name,
                    consultant2_response=consultant2_response,
                )},
            ],
        )
        return _extract_text(response)

    async def _client_reflect(
        self, agent: AgentSpec, question: str,
        problem_statement: str, consolidated_advice: str,
        consultant1_name: str, consultant2_name: str,
    ) -> str:
        """Phase 3: Client reflects on the advice (Opus, extended thinking)."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=16_000,
            thinking={
                "type": "enabled",
                "budget_tokens": self.thinking_budget,
            },
            system=agent.system_prompt,
            messages=[
                {"role": "user", "content": CLIENT_REFLECT_PROMPT.format(
                    role_description=agent.system_prompt,
                    question=question,
                    problem_statement=problem_statement,
                    consolidated_advice=consolidated_advice,
                    consultant1_name=consultant1_name,
                    consultant2_name=consultant2_name,
                )},
            ],
        )
        return _extract_text(response)

    async def _run_single_round(
        self, question: str, client: AgentSpec,
        consultant1: AgentSpec, consultant2: AgentSpec,
    ) -> TroikaRound:
        """Execute one full Troika round: present -> consult -> reflect."""
        t0 = time.time()

        # Phase 1: Client presents
        problem_statement = await self._client_present(client, question)

        # Phase 2: Consultation (sequential — consultant 2 reacts to consultant 1)
        c1_response = await self._consultant_initial(
            consultant1, question, client.name, problem_statement,
        )
        c2_response = await self._consultant_respond(
            consultant2, question, client.name, problem_statement,
            consultant1.name, c1_response,
        )

        # Phase 2c: Consolidate
        consolidated = await self._consolidate(
            question, client.name, problem_statement,
            consultant1.name, c1_response,
            consultant2.name, c2_response,
        )

        # Phase 3: Client reflects
        reflection = await self._client_reflect(
            client, question, problem_statement, consolidated,
            consultant1.name, consultant2.name,
        )

        return TroikaRound(
            client_name=client.name,
            consultants=[consultant1.name, consultant2.name],
            problem_statement=problem_statement,
            consultant1_response=c1_response,
            consultant2_response=c2_response,
            consolidated_advice=consolidated,
            client_reflection=reflection,
            elapsed_seconds=round(time.time() - t0, 2),
        )

    # ------------------------------------------------------------------
    # Main orchestration
    # ------------------------------------------------------------------

    async def run(self, question: str) -> TroikaResult:
        t0 = time.time()
        model_calls: dict[str, int] = {}
        timings: dict[str, float] = {}

        def _count(model: str, n: int = 1):
            model_calls[model] = model_calls.get(model, 0) + n

        rounds: list[TroikaRound] = []
        n = len(self.agents)

        # Each agent takes a turn as client; the next two agents are consultants
        for i in range(n):
            client = self.agents[i]
            consultant1 = self.agents[(i + 1) % n]
            consultant2 = self.agents[(i + 2) % n]

            round_t0 = time.time()
            troika_round = await self._run_single_round(
                question, client, consultant1, consultant2,
            )
            rounds.append(troika_round)

            # Per-round: 1 Opus (present) + 3 Haiku (c1, c2, consolidate) + 1 Opus (reflect)
            _count(self.thinking_model, 2)
            _count(self.orchestration_model, 3)
            timings[f"round_{i + 1}_{client.name}"] = round(time.time() - round_t0, 2)

        # Final synthesis (only if multiple rounds)
        final_synthesis = ""
        if len(rounds) > 1:
            synth_t0 = time.time()
            round_summaries = "\n\n---\n\n".join(
                f"**Round {i + 1} — Client: {r.client_name}, "
                f"Consultants: {', '.join(r.consultants)}**\n\n"
                f"**Problem Statement:**\n{r.problem_statement}\n\n"
                f"**Consolidated Advice:**\n{r.consolidated_advice}\n\n"
                f"**Client Reflection:**\n{r.client_reflection}"
                for i, r in enumerate(rounds)
            )
            response = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=16_000,
                thinking={
                    "type": "enabled",
                    "budget_tokens": self.thinking_budget,
                },
                messages=[
                    {"role": "user", "content": FINAL_SYNTHESIS_PROMPT.format(
                        question=question,
                        round_summaries=round_summaries,
                    )},
                ],
            )
            final_synthesis = _extract_text(response)
            _count(self.thinking_model)
            timings["final_synthesis"] = round(time.time() - synth_t0, 2)
        elif len(rounds) == 1:
            # Single round — the client reflection serves as the final output
            final_synthesis = rounds[0].client_reflection

        return TroikaResult(
            question=question,
            rounds=rounds,
            final_synthesis=final_synthesis,
            elapsed_seconds=round(time.time() - t0, 2),
            model_calls=model_calls,
            timings=timings,
        )
