"""P46: Incubation Protocol (The Walk) — Agent-agnostic orchestrator.

Load → Compress → Free-Associate → Evaluate. Creative incubation via
deliberate context-breaking between analytical and associative phases.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import anthropic
from protocols.langfuse_tracing import trace_protocol, create_span, end_span
from protocols.llm import extract_text, llm_complete, filter_exceptions

from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from .prompts import (
    ANALYSIS_PROMPT,
    COMPRESSION_PROMPT,
    EVALUATION_PROMPT,
    FREE_ASSOCIATION_PROMPT,
)


@dataclass
class IncubationResult:
    question: str
    prior_analysis: str = ""
    agent_analyses: dict[str, str] = field(default_factory=dict)
    core_tension: str = ""
    associations: str = ""
    reframes: str = ""
    synthesis: str = ""


class IncubationOrchestrator:
    """Runs the 4-phase Incubation (The Walk) protocol with any set of agents."""

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

    @trace_protocol("p46_incubation")
    async def run(self, question: str, prior_analysis: str = "") -> IncubationResult:
        """Execute the full Incubation protocol."""
        result = IncubationResult(question=question)

        # Phase 1: Load the Problem
        if prior_analysis:
            print("Phase 1: Using provided prior analysis (skipping agent analysis).")
            result.prior_analysis = prior_analysis
            analyses_text = prior_analysis
        else:
            print("Phase 1: Loading the problem — parallel agent analysis...")
            span = create_span("stage:load_problem", {"agent_count": len(self.agents)})
            try:
                raw_analyses = await self._analyze(question)
                result.agent_analyses = {
                    agent["name"]: raw_analyses[i]
                    for i, agent in enumerate(self.agents)
                }
                analyses_text = "\n\n".join(
                    f"=== {agent['name']} ===\n{text}"
                    for agent, text in zip(self.agents, raw_analyses)
                )
                end_span(span, output=f"{len(raw_analyses)} agent analyses")
            except Exception:
                end_span(span, error="load_problem failed")
                raise

        # Phase 2: Compress to Core Tension
        print("Phase 2: Compressing to core tension...")
        span = create_span("stage:compress", {})
        try:
            result.core_tension = await self._compress(question, analyses_text)
            print(f"  Tension: {result.core_tension}")
            end_span(span, output=f"tension: {result.core_tension[:200]}")
        except Exception:
            end_span(span, error="compress failed")
            raise

        # Phase 3: Free Association (The Walk)
        print("Phase 3: Free association (the walk)...")
        span = create_span("stage:free_association", {})
        try:
            result.associations = await self._free_associate(result.core_tension)
            end_span(span, output="associations generated")
        except Exception:
            end_span(span, error="free_association failed")
            raise

        # Phase 4: Evaluate and Translate
        print("Phase 4: Evaluating and translating...")
        span = create_span("stage:evaluate", {})
        try:
            evaluation = await self._evaluate(
                question, result.core_tension, result.associations, analyses_text
            )
            result.reframes = evaluation
            result.synthesis = evaluation
            end_span(span, output="evaluation complete")
        except Exception:
            end_span(span, error="evaluate failed")
            raise

        return result

    async def _analyze(self, question: str) -> list[str]:
        """Phase 1: All agents analyze the question in parallel."""
        prompt = ANALYSIS_PROMPT.format(question=question)

        async def query_agent(agent: dict) -> str:
            response = await llm_complete(
                self.client,
                model=self.thinking_model,
                max_tokens=self.thinking_budget + 4096,
                thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
                system=agent["system_prompt"],
                messages=[{"role": "user", "content": prompt}],
                agent_name=agent.get("name"),
            )
            return extract_text(response)

        _results = await asyncio.gather(
            *(query_agent(agent) for agent in self.agents),
            return_exceptions=True,
        )
        _results = filter_exceptions(_results, label="p46_incubation")
        return _results

    async def _compress(self, question: str, analyses: str) -> str:
        """Phase 2: Compress all analyses to the irreducible core tension."""
        response = await llm_complete(
            self.client,
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": COMPRESSION_PROMPT.format(
                    question=question, analyses=analyses
                ),
            }],
            agent_name="compression",
        )
        return extract_text(response).strip()

    async def _free_associate(self, tension: str) -> str:
        """Phase 3: Clean agent free-associates with no context. Temperature=1.0."""
        response = await llm_complete(
            self.client,
            model=self.thinking_model,
            max_tokens=4096,
            temperature=1.0,
            messages=[{
                "role": "user",
                "content": FREE_ASSOCIATION_PROMPT.format(tension=tension),
            }],
            agent_name="free_association",
        )
        return extract_text(response)

    async def _evaluate(
        self, question: str, tension: str, associations: str, analyses: str
    ) -> str:
        """Phase 4: Evaluate associations and translate back to strategy."""
        response = await llm_complete(
            self.client,
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": EVALUATION_PROMPT.format(
                    question=question,
                    tension=tension,
                    associations=associations,
                    analyses=analyses,
                ),
            }],
            agent_name="evaluation",
        )
        return extract_text(response)


