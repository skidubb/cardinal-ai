"""P38: Klein Pre-Mortem Protocol — Agent-agnostic orchestrator.

Gary Klein's prospective hindsight method: imagine the plan has already
failed, then work backwards to understand how.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

import anthropic
from protocols.langfuse_tracing import trace_protocol, create_span, end_span
from protocols.llm import extract_text, llm_complete, parse_json_object, filter_exceptions

from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from .prompts import (
    FAILURE_EXTRACTION_PROMPT,
    FAILURE_NARRATIVE_PROMPT,
    MITIGATION_SYNTHESIS_PROMPT,
)


@dataclass
class PreMortemResult:
    question: str
    time_horizon: str = "18 months"
    narratives: dict[str, str] = field(default_factory=dict)
    failure_modes: list[dict] = field(default_factory=list)
    overlooked_signals: list[str] = field(default_factory=list)
    mitigation_map: str = ""


class PreMortemOrchestrator:
    """Runs the 4-phase Klein Pre-Mortem protocol with any set of agents."""

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

    @trace_protocol("p38_klein_premortem")
    async def run(self, question: str, time_horizon: str = "18 months") -> PreMortemResult:
        """Execute the full Klein Pre-Mortem protocol."""
        result = PreMortemResult(question=question, time_horizon=time_horizon)

        # Phase 1: Frame (implicit — the prompt frames the pre-mortem)
        # Phase 2: Independent failure narratives (parallel)
        print("Phase 2: Generating independent failure narratives...")
        span = create_span("stage:failure_narratives", {"agent_count": len(self.agents)})
        try:
            narratives = await self._generate_narratives(question, time_horizon)
            result.narratives = {
                agent["name"]: narratives[i]
                for i, agent in enumerate(self.agents)
            }
            end_span(span, output=f"{len(narratives)} narratives generated")
        except Exception:
            end_span(span, error="failure_narratives failed")
            raise

        # Phase 3: Failure mode extraction
        print("Phase 3: Extracting failure modes...")
        span = create_span("stage:failure_extraction", {})
        try:
            all_text = "\n\n".join(
                f"=== {agent['name']} ===\n{narrative}"
                for agent, narrative in zip(self.agents, narratives)
            )
            extraction = await self._extract_failure_modes(all_text)
            result.failure_modes = extraction.get("failure_modes", [])
            result.overlooked_signals = extraction.get("overlooked_signals", [])
            end_span(span, output=f"{len(result.failure_modes)} failure modes extracted")
        except Exception:
            end_span(span, error="failure_extraction failed")
            raise

        # Phase 4: Mitigation synthesis
        print("Phase 4: Synthesizing mitigation map...")
        span = create_span("stage:mitigation_synthesis", {"failure_mode_count": len(result.failure_modes)})
        try:
            # Sort: convergent first, then unique
            sorted_modes = sorted(
                result.failure_modes,
                key=lambda m: (0 if m.get("type") == "convergent" else 1),
            )
            result.mitigation_map = await self._synthesize_mitigations(
                question, time_horizon, sorted_modes, result.overlooked_signals
            )
            end_span(span, output="mitigation map complete")
        except Exception:
            end_span(span, error="mitigation_synthesis failed")
            raise

        return result

    async def _generate_narratives(self, question: str, time_horizon: str) -> list[str]:
        """Phase 2: All agents write failure narratives in parallel."""
        prompt = FAILURE_NARRATIVE_PROMPT.format(
            question=question, time_horizon=time_horizon
        )

        async def query_agent(agent: dict) -> str:
            response = await llm_complete(
                self.client,
                model=self.thinking_model,
                max_tokens=self.thinking_budget + 4096,
                thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
                system=agent["system_prompt"],
                messages=[{"role": "user", "content": prompt}],
                agent_name=agent["name"],
            )
            return extract_text(response)

        _results = await asyncio.gather(
            *(query_agent(agent) for agent in self.agents),
            return_exceptions=True,
        )
        _results = filter_exceptions(_results, label="p38_klein_premortem")
        return _results

    async def _extract_failure_modes(self, all_narratives: str) -> dict:
        """Phase 3: Extract and classify failure modes using Haiku."""
        response = await llm_complete(
            self.client,
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": FAILURE_EXTRACTION_PROMPT.format(all_narratives=all_narratives),
            }],
            agent_name="failure_extraction",
        )
        return parse_json_object(extract_text(response))

    async def _synthesize_mitigations(
        self,
        question: str,
        time_horizon: str,
        failure_modes: list[dict],
        overlooked_signals: list[str],
    ) -> str:
        """Phase 4: Produce mitigation map using Opus with extended thinking."""
        response = await llm_complete(
            self.client,
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": MITIGATION_SYNTHESIS_PROMPT.format(
                    question=question,
                    time_horizon=time_horizon,
                    failure_modes_json=json.dumps(failure_modes, indent=2),
                    overlooked_signals="\n".join(f"- {s}" for s in overlooked_signals),
                ),
            }],
            agent_name="mitigation_synthesis",
        )
        return extract_text(response)




