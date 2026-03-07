"""P34: Goldratt Current Reality Tree — Agent-agnostic orchestrator.

Maps cause-and-effect from symptoms (UDEs) to root causes using sufficiency logic.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import anthropic
from protocols.langfuse_tracing import trace_protocol, create_span, end_span
from protocols.llm import extract_text, llm_complete, filter_exceptions

from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
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
        thinking_model: str = THINKING_MODEL,
        orchestration_model: str = ORCHESTRATION_MODEL,
        thinking_budget: int = 10_000,
    ):
        if not agents:
            raise ValueError("At least one agent is required")
        self.agents = agents
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    @trace_protocol("p34_current_reality_tree")
    async def run(self, question: str) -> CRTResult:
        """Execute the full Current Reality Tree protocol."""
        result = CRTResult(question=question)

        # Phase 1: Surface UDEs (parallel, all agents)
        print("Phase 1: Surfacing Undesirable Effects...")
        span = create_span("stage:surface_udes", {"agent_count": len(self.agents)})
        try:
            raw_udes = await self._surface_udes(question)
            result.udes = {
                agent["name"]: raw_udes[i]
                for i, agent in enumerate(self.agents)
            }
            end_span(span, output=f"{len(raw_udes)} UDE sets surfaced")
        except Exception:
            end_span(span, error="surface_udes failed")
            raise

        # Phase 2: Build Causal Chains
        print("Phase 2: Building causal chains...")
        span = create_span("stage:build_causal_tree", {})
        try:
            all_ude_text = "\n\n".join(
                f"=== {agent['name']} ===\n{raw}"
                for agent, raw in zip(self.agents, raw_udes)
            )
            result.causal_tree = await self._build_causal_tree(question, all_ude_text)
            end_span(span, output="causal tree built")
        except Exception:
            end_span(span, error="build_causal_tree failed")
            raise

        # Phase 3: Audit Logic
        print("Phase 3: Auditing logic with CLR tests...")
        span = create_span("stage:logic_audit", {})
        try:
            result.logic_audit = await self._audit_logic(question, result.causal_tree)
            end_span(span, output="logic audit complete")
        except Exception:
            end_span(span, error="logic_audit failed")
            raise

        # Phase 4: Synthesis
        print("Phase 4: Synthesizing root causes and recommendations...")
        span = create_span("stage:synthesis", {})
        try:
            result.synthesis = await self._synthesize(
                question, result.causal_tree, result.logic_audit
            )
            end_span(span, output="synthesis complete")
        except Exception:
            end_span(span, error="synthesis failed")
            raise

        return result

    async def _surface_udes(self, question: str) -> list[str]:
        """Phase 1: All agents surface UDEs in parallel."""
        prompt = UDE_GENERATION_PROMPT.format(question=question)

        async def query_agent(agent: dict) -> str:
            messages = [{"role": "user", "content": prompt}]
            response = await llm_complete(
                self.client,
                model=self.thinking_model,
                max_tokens=self.thinking_budget + 4096,
                thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
                system=agent["system_prompt"],
                messages=messages,
                agent_name=agent["name"],
            )
            return extract_text(response)

        _results = await asyncio.gather(
            *(query_agent(agent) for agent in self.agents),
            return_exceptions=True,
        )
        _results = filter_exceptions(_results, label="p34_current_reality_tree")
        return _results

    async def _build_causal_tree(self, question: str, all_udes: str) -> str:
        """Phase 2: Tree Builder constructs causal chain from UDEs."""
        response = await llm_complete(
            self.client,
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": CAUSAL_CHAIN_PROMPT.format(
                    question=question, all_udes=all_udes
                ),
            }],
            agent_name="tree_builder",
        )
        return extract_text(response)

    async def _audit_logic(self, question: str, causal_tree: str) -> str:
        """Phase 3: Logic Auditor validates causal links using CLR."""
        response = await llm_complete(
            self.client,
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": LOGIC_AUDIT_PROMPT.format(
                    question=question, causal_tree=causal_tree
                ),
            }],
            agent_name="logic_auditor",
        )
        return extract_text(response)

    async def _synthesize(
        self, question: str, causal_tree: str, logic_audit: str
    ) -> str:
        """Phase 4: Produce final root cause analysis and recommendations."""
        response = await llm_complete(
            self.client,
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
            agent_name="synthesis",
        )
        return extract_text(response)


