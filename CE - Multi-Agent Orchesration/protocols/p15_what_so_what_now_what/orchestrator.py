"""P15: What / So What / Now What — Three-frame temporal analysis orchestrator."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import anthropic

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


def _extract_text(response) -> str:
    """Pull plain text from an Anthropic API response."""
    for block in response.content:
        if block.type == "text":
            return block.text
    return ""


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
        self.thinking_model = thinking_model or "claude-opus-4-6"
        self.orchestration_model = orchestration_model or "claude-haiku-4-5-20251001"
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _think(self, agent: dict[str, str], prompt: str) -> str:
        """Call thinking model with extended thinking for an agent."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=16_000,
            thinking={
                "type": "enabled",
                "budget_tokens": self.thinking_budget,
            },
            system=agent["system_prompt"],
            messages=[{"role": "user", "content": prompt}],
        )
        return _extract_text(response)

    async def _orchestrate(self, prompt: str) -> str:
        """Call orchestration model (Haiku) for consolidation."""
        response = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=8_000,
            messages=[{"role": "user", "content": prompt}],
        )
        return _extract_text(response)

    def _count(self, calls: dict[str, int], model: str, n: int = 1) -> None:
        calls[model] = calls.get(model, 0) + n

    # ------------------------------------------------------------------
    # Main orchestration
    # ------------------------------------------------------------------

    async def run(self, question: str) -> WhatSoWhatNowWhatResult:
        timings: dict[str, float] = {}
        model_calls: dict[str, int] = {}

        # --- Phase 1: WHAT — parallel observations (Opus) ---
        t0 = time.time()
        what_tasks = [
            self._think(agent, WHAT_PROMPT.format(question=question))
            for agent in self.agents
        ]
        what_texts = await asyncio.gather(*what_tasks)
        self._count(model_calls, self.thinking_model, len(self.agents))
        timings["phase1_what"] = round(time.time() - t0, 2)

        what_observations: dict[str, str] = {}
        for agent, text in zip(self.agents, what_texts):
            what_observations[agent["name"]] = text

        # --- Phase 2: Consolidate observations (Haiku) ---
        t0 = time.time()
        obs_block = "\n\n---\n\n".join(
            f"**{name}:**\n{text}" for name, text in what_observations.items()
        )
        consolidated_observations = await self._orchestrate(
            CONSOLIDATE_OBSERVATIONS_PROMPT.format(
                question=question, observations=obs_block
            )
        )
        self._count(model_calls, self.orchestration_model)
        timings["phase2_consolidate_observations"] = round(time.time() - t0, 2)

        # --- Phase 3: SO WHAT — parallel implications (Opus) ---
        t0 = time.time()
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
        so_what_texts = await asyncio.gather(*so_what_tasks)
        self._count(model_calls, self.thinking_model, len(self.agents))
        timings["phase3_so_what"] = round(time.time() - t0, 2)

        so_what_implications: dict[str, str] = {}
        for agent, text in zip(self.agents, so_what_texts):
            so_what_implications[agent["name"]] = text

        # --- Phase 4: Consolidate implications (Haiku) ---
        t0 = time.time()
        impl_block = "\n\n---\n\n".join(
            f"**{name}:**\n{text}" for name, text in so_what_implications.items()
        )
        consolidated_implications = await self._orchestrate(
            CONSOLIDATE_IMPLICATIONS_PROMPT.format(
                question=question,
                consolidated_observations=consolidated_observations,
                implications=impl_block,
            )
        )
        self._count(model_calls, self.orchestration_model)
        timings["phase4_consolidate_implications"] = round(time.time() - t0, 2)

        # --- Phase 5: NOW WHAT — parallel actions (Opus) ---
        t0 = time.time()
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
        now_what_texts = await asyncio.gather(*now_what_tasks)
        self._count(model_calls, self.thinking_model, len(self.agents))
        timings["phase5_now_what"] = round(time.time() - t0, 2)

        now_what_actions: dict[str, str] = {}
        for agent, text in zip(self.agents, now_what_texts):
            now_what_actions[agent["name"]] = text

        # --- Phase 6: Final synthesis (Opus) ---
        t0 = time.time()
        actions_block = "\n\n---\n\n".join(
            f"**{name}:**\n{text}" for name, text in now_what_actions.items()
        )
        response = await self.client.messages.create(
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
        )
        final_synthesis = _extract_text(response)
        self._count(model_calls, self.thinking_model)
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
