"""P28: Parallel Thinking (Six Hats) Protocol — Agent-agnostic orchestrator.

All agents wear the SAME hat simultaneously. Hats replace personas.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import anthropic

from .prompts import (
    BLACK_HAT_PROMPT,
    BLUE_HAT_FRAMING_PROMPT,
    BLUE_HAT_SYNTHESIS_PROMPT,
    GREEN_HAT_PROMPT,
    RED_HAT_PROMPT,
    WHITE_HAT_PROMPT,
    YELLOW_HAT_PROMPT,
)


@dataclass
class SixHatsResult:
    question: str
    framing: str = ""
    hat_outputs: dict[str, dict[str, str]] = field(default_factory=dict)
    synthesis: str = ""


class SixHatsOrchestrator:
    """Runs the 7-phase Six Thinking Hats protocol with any set of agents."""

    def __init__(
        self,
        agents: list[dict],
        thinking_model: str = "claude-opus-4-6",
        orchestration_model: str = "claude-haiku-4-5-20251001",
        thinking_budget: int = 10_000,
    ):
        """
        Args:
            agents: List of {"name": str, "system_prompt": str} dicts.
                    Any agents work — C-Suite, GTM, custom, etc.
            thinking_model: Model for agent reasoning (hat phases, synthesis).
            orchestration_model: Model for mechanical steps (framing).
            thinking_budget: Token budget for extended thinking on Opus calls.
        """
        if not agents:
            raise ValueError("At least one agent is required")
        self.agents = agents
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    async def run(self, question: str) -> SixHatsResult:
        """Execute the full Six Thinking Hats protocol."""
        result = SixHatsResult(question=question)

        # Phase 1: Blue Hat — Frame
        print("Phase 1: Blue Hat — Framing the question...")
        result.framing = await self._blue_hat_frame(question)

        # Phase 2: White Hat — Facts
        print("Phase 2: White Hat — Facts only...")
        result.hat_outputs["white"] = await self._run_hat(
            question, WHITE_HAT_PROMPT, use_thinking=True
        )

        # Phase 3: Red Hat — Emotions (no thinking, short responses)
        print("Phase 3: Red Hat — Emotional reactions...")
        result.hat_outputs["red"] = await self._run_hat(
            question, RED_HAT_PROMPT, use_thinking=False
        )

        # Phase 4: Black Hat — Caution
        print("Phase 4: Black Hat — Risks and caution...")
        result.hat_outputs["black"] = await self._run_hat(
            question, BLACK_HAT_PROMPT, use_thinking=True
        )

        # Phase 5: Yellow Hat — Optimism
        print("Phase 5: Yellow Hat — Benefits and opportunities...")
        result.hat_outputs["yellow"] = await self._run_hat(
            question, YELLOW_HAT_PROMPT, use_thinking=True
        )

        # Phase 6: Green Hat — Creativity
        print("Phase 6: Green Hat — Creative alternatives...")
        result.hat_outputs["green"] = await self._run_hat(
            question, GREEN_HAT_PROMPT, use_thinking=True
        )

        # Phase 7: Blue Hat — Synthesis
        print("Phase 7: Blue Hat — Synthesizing all perspectives...")
        result.synthesis = await self._blue_hat_synthesize(question, result.hat_outputs)

        return result

    async def _blue_hat_frame(self, question: str) -> str:
        """Phase 1: Blue Hat framing (orchestrator only, Haiku)."""
        response = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": BLUE_HAT_FRAMING_PROMPT.format(question=question),
            }],
        )
        return response.content[0].text

    async def _run_hat(
        self, question: str, prompt_template: str, *, use_thinking: bool
    ) -> dict[str, str]:
        """Run a single hat phase across all agents in parallel.

        Agents' normal system_prompt is IGNORED — the hat prompt replaces it.
        """
        prompt = prompt_template.format(question=question)

        async def query_agent(agent: dict) -> tuple[str, str]:
            messages = [{"role": "user", "content": prompt}]
            if use_thinking:
                response = await self.client.messages.create(
                    model=self.thinking_model,
                    max_tokens=self.thinking_budget + 4096,
                    thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
                    messages=messages,
                )
            else:
                response = await self.client.messages.create(
                    model=self.thinking_model,
                    max_tokens=512,
                    messages=messages,
                )
            return agent["name"], _extract_text(response)

        results = await asyncio.gather(
            *(query_agent(agent) for agent in self.agents)
        )
        return dict(results)

    async def _blue_hat_synthesize(
        self, question: str, hat_outputs: dict[str, dict[str, str]]
    ) -> str:
        """Phase 7: Blue Hat synthesis (orchestrator only, Opus+thinking)."""

        def format_hat(hat_name: str) -> str:
            outputs = hat_outputs.get(hat_name, {})
            return "\n\n".join(
                f"--- {name} ---\n{text}" for name, text in outputs.items()
            )

        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": BLUE_HAT_SYNTHESIS_PROMPT.format(
                    question=question,
                    white_hat_outputs=format_hat("white"),
                    red_hat_outputs=format_hat("red"),
                    black_hat_outputs=format_hat("black"),
                    yellow_hat_outputs=format_hat("yellow"),
                    green_hat_outputs=format_hat("green"),
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
