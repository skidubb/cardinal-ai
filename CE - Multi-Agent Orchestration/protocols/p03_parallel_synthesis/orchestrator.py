"""P3: Parallel Synthesis Protocol — Agent-agnostic orchestrator.

All agents answer independently → synthesizer merges into unified recommendation.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from protocols.langfuse_tracing import trace_protocol, create_span, end_span
from protocols.llm import agent_complete, extract_text, filter_exceptions
from protocols.synthesis import SynthesisEngine
from protocols.tracing import make_client
from .prompts import SYNTHESIS_SYSTEM_PROMPT
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL


@dataclass
class AgentPerspective:
    name: str
    response: str


@dataclass
class SynthesisResult:
    question: str
    perspectives: list[AgentPerspective] = field(default_factory=list)
    synthesis: str = ""


class SynthesisOrchestrator:
    """Runs the 2-stage Parallel Synthesis protocol with any set of agents."""

    def __init__(
        self,
        agents: list[dict],
        thinking_model: str = THINKING_MODEL,
        orchestration_model: str = ORCHESTRATION_MODEL,
        thinking_budget: int = 10_000,
        trace: bool = False,
        trace_path: str | None = None,
        synthesis_engine: SynthesisEngine | None = None,
    ):
        """
        Args:
            agents: List of {"name": str, "system_prompt": str} dicts.
            thinking_model: Model for agent reasoning and synthesis.
            orchestration_model: Not used in P3 (all stages are thinking tasks),
                                 kept for API consistency across protocols.
            thinking_budget: Token budget for extended thinking on Opus calls.
            trace: Enable JSONL execution tracing.
            synthesis_engine: Optional SynthesisEngine instance. If None, one is
                              created with use_agent=True.
        """
        if not agents:
            raise ValueError("At least one agent is required")
        self.agents = agents
        self.thinking_model = thinking_model
        self.thinking_budget = thinking_budget
        self.client = make_client(protocol_id="p03_parallel_synthesis", trace=trace, trace_path=Path(trace_path) if trace_path else None)
        self._synth = synthesis_engine or SynthesisEngine(
            self.client, thinking_model, thinking_budget, use_agent=True
        )

    @trace_protocol("p03_parallel_synthesis")
    async def run(self, question: str) -> SynthesisResult:
        """Execute the full Parallel Synthesis protocol."""
        result = SynthesisResult(question=question)

        # Stage 1: Parallel query — all agents answer independently
        print(f"Stage 1: Querying {len(self.agents)} agents in parallel...")
        span = create_span("stage:parallel_query", {"agent_count": len(self.agents)})
        try:
            responses = await self._parallel_query(question)
            result.perspectives = [
                AgentPerspective(name=agent["name"], response=resp)
                for agent, resp in zip(self.agents, responses)
            ]
            end_span(span, output=f"{len(responses)} perspectives")
        except Exception:
            end_span(span, error="parallel_query failed")
            raise

        # Stage 2: Synthesis — merge all perspectives
        print("Stage 2: Synthesizing perspectives...")
        span = create_span("stage:synthesis", {"perspective_count": len(result.perspectives)})
        try:
            result.synthesis = await self._synthesize(question, result.perspectives)
            end_span(span, output=f"synthesis {len(result.synthesis)} chars")
        except Exception:
            end_span(span, error="synthesis failed")
            raise

        return result

    async def _parallel_query(self, question: str) -> list[str]:
        """Stage 1: All agents answer the question in parallel."""

        async def query_agent(agent: dict) -> str:
            return await agent_complete(
                agent=agent,
                fallback_model=self.thinking_model,
                messages=[{"role": "user", "content": question}],
                thinking_budget=self.thinking_budget,
                anthropic_client=self.client,
            )

        _results = await asyncio.gather(
            *(query_agent(agent) for agent in self.agents),
            return_exceptions=True,
        )
        _results = filter_exceptions(_results, label="p03_parallel_synthesis")
        return _results

    async def _synthesize(
        self, question: str, perspectives: list[AgentPerspective]
    ) -> str:
        """Stage 2: Synthesize all perspectives into a unified recommendation."""
        perspectives_text = "\n\n".join(
            f"=== {p.name} ===\n{p.response}" for p in perspectives
        )
        prompt = (
            f"ORIGINAL QUESTION:\n{question}\n\n"
            f"INDEPENDENT PERSPECTIVES:\n{perspectives_text}"
        )
        return await self._synth.synthesize(
            protocol_prompt=prompt,
            question=question,
            system_prompt=SYNTHESIS_SYSTEM_PROMPT,
        )
