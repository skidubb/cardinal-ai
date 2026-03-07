"""P15: What / So What / Now What — Three-frame temporal analysis orchestrator."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

import anthropic
from protocols.langfuse_tracing import trace_protocol, create_span, end_span
from protocols.llm import extract_text, llm_complete, filter_exceptions

from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from .prompts import (
    CONSOLIDATE_IMPLICATIONS_PROMPT,
    CONSOLIDATE_OBSERVATIONS_PROMPT,
    FINAL_SYNTHESIS_PROMPT,
    NOW_WHAT_PROMPT,
    SO_WHAT_PROMPT,
    WHAT_PROMPT,
)


@dataclass
class WhatSoWhatNowWhatResult:
    """Complete result from a What/So What/Now What run."""

    question: str
    what_observations: dict[str, str]
    consolidated_observations: str
    so_what_implications: dict[str, str]
    consolidated_implications: str
    now_what_actions: dict[str, str]
    final_synthesis: str
    timings: dict[str, float] = field(default_factory=dict)
    model_calls: dict[str, int] = field(default_factory=dict)




class WhatSoWhatNowWhatOrchestrator:
    """Runs the What / So What / Now What three-frame protocol."""

    def __init__(
        self,
        agents: list[dict[str, str]],
        thinking_model: str | None = None,
        orchestration_model: str | None = None,
        thinking_budget: int = 10_000,
    ):
        self.agents = agents
        self.thinking_model = thinking_model or THINKING_MODEL
        self.orchestration_model = orchestration_model or ORCHESTRATION_MODEL
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _think(self, agent: dict[str, str], prompt: str) -> str:
        """Call thinking model with extended thinking for an agent."""
        response = await llm_complete(
            self.client,
            model=self.thinking_model,
            max_tokens=16_000,
            thinking={
                "type": "enabled",
                "budget_tokens": self.thinking_budget,
            },
            system=agent["system_prompt"],
            messages=[{"role": "user", "content": prompt}],
            agent_name=agent["name"],
        )
        return extract_text(response)

    async def _orchestrate(self, prompt: str, stage_label: str = "consolidation") -> str:
        """Call orchestration model (Haiku) for consolidation."""
        response = await llm_complete(
            self.client,
            model=self.orchestration_model,
            max_tokens=8_000,
            messages=[{"role": "user", "content": prompt}],
            agent_name=stage_label,
        )
        return extract_text(response)

    def _count(self, calls: dict[str, int], model: str, n: int = 1) -> None:
        calls[model] = calls.get(model, 0) + n

    # ------------------------------------------------------------------
    # Main orchestration
    # ------------------------------------------------------------------

    @trace_protocol("p15_what_so_what_now_what")
    async def run(self, question: str) -> WhatSoWhatNowWhatResult:
        timings: dict[str, float] = {}
        model_calls: dict[str, int] = {}

        # --- Phase 1: WHAT — parallel observations (Opus) ---
        t0 = time.time()
        span = create_span("stage:what_observations", {"agent_count": len(self.agents)})
        try:
            what_tasks = [
                self._think(agent, WHAT_PROMPT.format(question=question))
                for agent in self.agents
            ]
            what_texts = await asyncio.gather(*what_tasks, return_exceptions=True)
            what_texts = filter_exceptions(what_texts, label="p15_what_so_what_now_what")
            self._count(model_calls, self.thinking_model, len(self.agents))
            end_span(span, output=f"{len(what_texts)} observations collected")
        except Exception:
            end_span(span, error="what_observations failed")
            raise
        timings["phase1_what"] = round(time.time() - t0, 2)

        what_observations: dict[str, str] = {}
        for agent, text in zip(self.agents, what_texts):
            what_observations[agent["name"]] = text

        # --- Phase 2: Consolidate observations (Haiku) ---
        t0 = time.time()
        span = create_span("stage:consolidate_observations", {})
        try:
            obs_block = "\n\n---\n\n".join(
                f"**{name}:**\n{text}" for name, text in what_observations.items()
            )
            consolidated_observations = await self._orchestrate(
                CONSOLIDATE_OBSERVATIONS_PROMPT.format(
                    question=question, observations=obs_block
                ),
                stage_label="consolidate_observations",
            )
            self._count(model_calls, self.orchestration_model)
            end_span(span, output="observations consolidated")
        except Exception:
            end_span(span, error="consolidate_observations failed")
            raise
        timings["phase2_consolidate_observations"] = round(time.time() - t0, 2)

        # --- Phase 3: SO WHAT — parallel implications (Opus) ---
        t0 = time.time()
        span = create_span("stage:so_what_implications", {"agent_count": len(self.agents)})
        try:
            so_what_tasks = [
                self._think(
                    agent,
                    SO_WHAT_PROMPT.format(
                        question=question,
                        consolidated_observations=consolidated_observations,
                    ),
                )
                for agent in self.agents
            ]
            so_what_texts = await asyncio.gather(*so_what_tasks, return_exceptions=True)
            so_what_texts = filter_exceptions(so_what_texts, label="p15_what_so_what_now_what")
            self._count(model_calls, self.thinking_model, len(self.agents))
            end_span(span, output=f"{len(so_what_texts)} implications collected")
        except Exception:
            end_span(span, error="so_what_implications failed")
            raise
        timings["phase3_so_what"] = round(time.time() - t0, 2)

        so_what_implications: dict[str, str] = {}
        for agent, text in zip(self.agents, so_what_texts):
            so_what_implications[agent["name"]] = text

        # --- Phase 4: Consolidate implications (Haiku) ---
        t0 = time.time()
        span = create_span("stage:consolidate_implications", {})
        try:
            impl_block = "\n\n---\n\n".join(
                f"**{name}:**\n{text}" for name, text in so_what_implications.items()
            )
            consolidated_implications = await self._orchestrate(
                CONSOLIDATE_IMPLICATIONS_PROMPT.format(
                    question=question,
                    consolidated_observations=consolidated_observations,
                    implications=impl_block,
                ),
                stage_label="consolidate_implications",
            )
            self._count(model_calls, self.orchestration_model)
            end_span(span, output="implications consolidated")
        except Exception:
            end_span(span, error="consolidate_implications failed")
            raise
        timings["phase4_consolidate_implications"] = round(time.time() - t0, 2)

        # --- Phase 5: NOW WHAT — parallel actions (Opus) ---
        t0 = time.time()
        span = create_span("stage:now_what_actions", {"agent_count": len(self.agents)})
        try:
            now_what_tasks = [
                self._think(
                    agent,
                    NOW_WHAT_PROMPT.format(
                        question=question,
                        consolidated_observations=consolidated_observations,
                        consolidated_implications=consolidated_implications,
                    ),
                )
                for agent in self.agents
            ]
            now_what_texts = await asyncio.gather(*now_what_tasks, return_exceptions=True)
            now_what_texts = filter_exceptions(now_what_texts, label="p15_what_so_what_now_what")
            self._count(model_calls, self.thinking_model, len(self.agents))
            end_span(span, output=f"{len(now_what_texts)} action plans collected")
        except Exception:
            end_span(span, error="now_what_actions failed")
            raise
        timings["phase5_now_what"] = round(time.time() - t0, 2)

        now_what_actions: dict[str, str] = {}
        for agent, text in zip(self.agents, now_what_texts):
            now_what_actions[agent["name"]] = text

        # --- Phase 6: Final synthesis (Opus) ---
        t0 = time.time()
        span = create_span("stage:final_synthesis", {})
        try:
            actions_block = "\n\n---\n\n".join(
                f"**{name}:**\n{text}" for name, text in now_what_actions.items()
            )
            response = await llm_complete(
                self.client,
                model=self.thinking_model,
                max_tokens=16_000,
                thinking={
                    "type": "enabled",
                    "budget_tokens": self.thinking_budget,
                },
                messages=[
                    {
                        "role": "user",
                        "content": FINAL_SYNTHESIS_PROMPT.format(
                            question=question,
                            consolidated_observations=consolidated_observations,
                            consolidated_implications=consolidated_implications,
                            now_what_actions=actions_block,
                        ),
                    }
                ],
                agent_name="final_synthesis",
            )
            final_synthesis = extract_text(response)
            self._count(model_calls, self.thinking_model)
            end_span(span, output="final synthesis completed")
        except Exception:
            end_span(span, error="final_synthesis failed")
            raise
        timings["phase6_final_synthesis"] = round(time.time() - t0, 2)

        return WhatSoWhatNowWhatResult(
            question=question,
            what_observations=what_observations,
            consolidated_observations=consolidated_observations,
            so_what_implications=so_what_implications,
            consolidated_implications=consolidated_implications,
            now_what_actions=now_what_actions,
            final_synthesis=final_synthesis,
            timings=timings,
            model_calls=model_calls,
        )
