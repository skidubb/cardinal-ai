"""P34: Goldratt Current Reality Tree — Agent-agnostic orchestrator.

Maps cause-and-effect from symptoms (UDEs) to root causes using sufficiency logic.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import anthropic

from .prompts import (
    CAUSAL_CHAIN_PROMPT,
    LOGIC_AUDIT_PROMPT,
    SYNTHESIS_PROMPT,
    UDE_GENERATION_PROMPT,
)


@dataclass
class CRTResult:
    question: str
    udes: dict[str, str] = field(default_factory=dict)
    causal_tree: str = ""
    logic_audit: str = ""
    root_causes: str = ""
    synthesis: str = ""


class CRTOrchestrator:
    """Runs the 4-phase Current Reality Tree protocol with any set of agents."""

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

    async def run(self, question: str) -> CRTResult:
        """Execute the full Current Reality Tree protocol."""
        result = CRTResult(question=question)

        # Phase 1: Surface UDEs (parallel, all agents)
        print("Phase 1: Surfacing Undesirable Effects...")
        raw_udes = await self._surface_udes(question)
        result.udes = {
            agent["name"]: raw_udes[i]
            for i, agent in enumerate(self.agents)
        }

        # Phase 2: Build Causal Chains
        print("Phase 2: Building causal chains...")
        all_ude_text = "\n\n".join(
            f"=== {agent['name']} ===\n{raw}"
            for agent, raw in zip(self.agents, raw_udes)
        )
        result.causal_tree = await self._build_causal_tree(question, all_ude_text)

        # Phase 3: Audit Logic
        print("Phase 3: Auditing logic with CLR tests...")
        result.logic_audit = await self._audit_logic(question, result.causal_tree)

        # Phase 4: Synthesis
        print("Phase 4: Synthesizing root causes and recommendations...")
        result.synthesis = await self._synthesize(
            question, result.causal_tree, result.logic_audit
        )

        return result

    async def _surface_udes(self, question: str) -> list[str]:
        """Phase 1: All agents surface UDEs in parallel."""
        prompt = UDE_GENERATION_PROMPT.format(question=question)

        async def query_agent(agent: dict) -> str:
            messages = [{"role": "user", "content": prompt}]
            response = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=self.thinking_budget + 4096,
                thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
                system=agent["system_prompt"],
                messages=messages,
            )
            return _extract_text(response)

        return await asyncio.gather(
            *(query_agent(agent) for agent in self.agents)
        )

    async def _build_causal_tree(self, question: str, all_udes: str) -> str:
        """Phase 2: Tree Builder constructs causal chain from UDEs."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": CAUSAL_CHAIN_PROMPT.format(
                    question=question, all_udes=all_udes
                ),
            }],
        )
        return _extract_text(response)

    async def _audit_logic(self, question: str, causal_tree: str) -> str:
        """Phase 3: Logic Auditor validates causal links using CLR."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": LOGIC_AUDIT_PROMPT.format(
                    question=question, causal_tree=causal_tree
                ),
            }],
        )
        return _extract_text(response)

    async def _synthesize(
        self, question: str, causal_tree: str, logic_audit: str
    ) -> str:
        """Phase 4: Produce final root cause analysis and recommendations."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": SYNTHESIS_PROMPT.format(
                    question=question,
                    causal_tree=causal_tree,
                    logic_audit=logic_audit,
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
