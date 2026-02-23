"""P36: Peirce Abduction Cycle — Agent-agnostic orchestrator.

Iterative abduction → deduction → induction loop for explanatory reasoning.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field

import anthropic

from .prompts import (
    ABDUCTION_PROMPT,
    DEDUCTION_PROMPT,
    INDUCTION_PROMPT,
    LOOP_DECISION_PROMPT,
    SYNTHESIS_PROMPT,
)


@dataclass
class AbductionResult:
    question: str
    cycles: list[dict] = field(default_factory=list)
    final_hypothesis: str = ""
    synthesis: str = ""


class AbductionOrchestrator:
    """Runs the Peirce Abduction Cycle with any set of agents."""

    def __init__(
        self,
        agents: list[dict],
        thinking_model: str = "claude-opus-4-6",
        orchestration_model: str = "claude-haiku-4-5-20251001",
        thinking_budget: int = 10_000,
        max_cycles: int = 3,
    ):
        if not agents:
            raise ValueError("At least one agent is required")
        self.agents = agents
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.max_cycles = max_cycles
        self.client = anthropic.AsyncAnthropic()

    async def run(self, question: str) -> AbductionResult:
        """Execute the Peirce Abduction Cycle."""
        result = AbductionResult(question=question)
        anomaly = question

        for cycle_num in range(1, self.max_cycles + 1):
            print(f"\n--- Cycle {cycle_num} ---")
            cycle = {"cycle_number": cycle_num, "anomaly": anomaly}

            # Phase 1: Abduction
            print("Phase 1: Abduction — generating hypotheses...")
            hypotheses = await self._abduction(anomaly)
            cycle["hypotheses"] = hypotheses

            # Phase 2: Deduction
            print("Phase 2: Deduction — deriving predictions...")
            predictions = await self._deduction(anomaly, hypotheses)
            cycle["predictions"] = predictions

            # Phase 3: Induction
            print("Phase 3: Induction — testing against evidence...")
            evidence = await self._induction(anomaly, hypotheses, predictions)
            cycle["evidence_assessment"] = evidence

            # Loop decision
            print("Evaluating cycle outcome...")
            decision = await self._loop_decision(anomaly, evidence)
            outcome = decision.get("outcome", "CONTINUE")

            if cycle_num == self.max_cycles and outcome == "CONTINUE":
                outcome = "EXHAUSTED"

            cycle["outcome"] = outcome
            result.cycles.append(cycle)

            if outcome == "ACCEPT":
                result.final_hypothesis = decision.get("accepted_hypothesis", "")
                print(f"ACCEPTED: {result.final_hypothesis}")
                break
            elif outcome == "EXHAUSTED":
                print("Max cycles reached without acceptance.")
                break
            else:
                anomaly = decision.get("new_anomaly", anomaly)
                print(f"CONTINUING with new anomaly: {anomaly[:100]}...")

        # Final synthesis
        print("\nSynthesizing final briefing...")
        result.synthesis = await self._synthesize(question, result.cycles)

        return result

    async def _abduction(self, anomaly: str) -> str:
        """Phase 1: Agents generate hypotheses in parallel."""
        prompt = ABDUCTION_PROMPT.format(anomaly=anomaly)

        async def query_agent(agent: dict) -> str:
            response = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=self.thinking_budget + 4096,
                thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
                system=agent["system_prompt"],
                messages=[{"role": "user", "content": prompt}],
            )
            return _extract_text(response)

        responses = await asyncio.gather(
            *(query_agent(agent) for agent in self.agents)
        )
        return "\n\n".join(
            f"=== {agent['name']} ===\n{resp}"
            for agent, resp in zip(self.agents, responses)
        )

    async def _deduction(self, anomaly: str, hypotheses: str) -> str:
        """Phase 2: Agents derive predictions in parallel."""
        prompt = DEDUCTION_PROMPT.format(anomaly=anomaly, hypotheses=hypotheses)

        async def query_agent(agent: dict) -> str:
            response = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=self.thinking_budget + 4096,
                thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
                system=agent["system_prompt"],
                messages=[{"role": "user", "content": prompt}],
            )
            return _extract_text(response)

        responses = await asyncio.gather(
            *(query_agent(agent) for agent in self.agents)
        )
        return "\n\n".join(
            f"=== {agent['name']} ===\n{resp}"
            for agent, resp in zip(self.agents, responses)
        )

    async def _induction(self, anomaly: str, hypotheses: str, predictions: str) -> str:
        """Phase 3: Agents test predictions against evidence in parallel."""
        prompt = INDUCTION_PROMPT.format(
            anomaly=anomaly, hypotheses=hypotheses, predictions=predictions
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

        responses = await asyncio.gather(
            *(query_agent(agent) for agent in self.agents)
        )
        return "\n\n".join(
            f"=== {agent['name']} ===\n{resp}"
            for agent, resp in zip(self.agents, responses)
        )

    async def _loop_decision(self, anomaly: str, evidence_assessment: str) -> dict:
        """Decide whether to ACCEPT or CONTINUE."""
        response = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": LOOP_DECISION_PROMPT.format(
                    anomaly=anomaly, evidence_assessment=evidence_assessment
                ),
            }],
        )
        return _parse_json_object(response.content[0].text)

    async def _synthesize(self, question: str, cycles: list[dict]) -> str:
        """Produce final briefing across all cycles."""
        cycle_history = json.dumps(cycles, indent=2, default=str)
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": SYNTHESIS_PROMPT.format(
                    question=question, cycle_history=cycle_history
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
