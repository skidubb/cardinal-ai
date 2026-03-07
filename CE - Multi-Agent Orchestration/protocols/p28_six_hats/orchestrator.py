"""P28: Parallel Thinking (Six Hats) Protocol — Agent-agnostic orchestrator.

All agents wear the SAME hat simultaneously. Hats replace personas.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import anthropic
from protocols.langfuse_tracing import trace_protocol, create_span, end_span
from protocols.llm import extract_text, llm_complete, filter_exceptions

from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
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
        thinking_model: str = THINKING_MODEL,
        orchestration_model: str = ORCHESTRATION_MODEL,
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

    @trace_protocol("p28_six_hats")
    async def run(self, question: str) -> SixHatsResult:
        """Execute the full Six Thinking Hats protocol."""
        result = SixHatsResult(question=question)

        # Phase 1: Blue Hat — Frame
        print("Phase 1: Blue Hat — Framing the question...")
        span = create_span("stage:blue_hat_framing", {"agent_count": len(self.agents)})
        try:
            result.framing = await self._blue_hat_frame(question)
            end_span(span, output="framing complete")
        except Exception:
            end_span(span, error="blue_hat_framing failed")
            raise

        # Phase 2: White Hat — Facts
        print("Phase 2: White Hat — Facts only...")
        span = create_span("stage:white_hat", {"agent_count": len(self.agents)})
        try:
            result.hat_outputs["white"] = await self._run_hat(
                question, WHITE_HAT_PROMPT, use_thinking=True
            )
            end_span(span, output=f"{len(result.hat_outputs['white'])} agent responses")
        except Exception:
            end_span(span, error="white_hat failed")
            raise

        # Phase 3: Red Hat — Emotions (no thinking, short responses)
        print("Phase 3: Red Hat — Emotional reactions...")
        span = create_span("stage:red_hat", {"agent_count": len(self.agents)})
        try:
            result.hat_outputs["red"] = await self._run_hat(
                question, RED_HAT_PROMPT, use_thinking=False
            )
            end_span(span, output=f"{len(result.hat_outputs['red'])} agent responses")
        except Exception:
            end_span(span, error="red_hat failed")
            raise

        # Phase 4: Black Hat — Caution
        print("Phase 4: Black Hat — Risks and caution...")
        span = create_span("stage:black_hat", {"agent_count": len(self.agents)})
        try:
            result.hat_outputs["black"] = await self._run_hat(
                question, BLACK_HAT_PROMPT, use_thinking=True
            )
            end_span(span, output=f"{len(result.hat_outputs['black'])} agent responses")
        except Exception:
            end_span(span, error="black_hat failed")
            raise

        # Phase 5: Yellow Hat — Optimism
        print("Phase 5: Yellow Hat — Benefits and opportunities...")
        span = create_span("stage:yellow_hat", {"agent_count": len(self.agents)})
        try:
            result.hat_outputs["yellow"] = await self._run_hat(
                question, YELLOW_HAT_PROMPT, use_thinking=True
            )
            end_span(span, output=f"{len(result.hat_outputs['yellow'])} agent responses")
        except Exception:
            end_span(span, error="yellow_hat failed")
            raise

        # Phase 6: Green Hat — Creativity
        print("Phase 6: Green Hat — Creative alternatives...")
        span = create_span("stage:green_hat", {"agent_count": len(self.agents)})
        try:
            result.hat_outputs["green"] = await self._run_hat(
                question, GREEN_HAT_PROMPT, use_thinking=True
            )
            end_span(span, output=f"{len(result.hat_outputs['green'])} agent responses")
        except Exception:
            end_span(span, error="green_hat failed")
            raise

        # Phase 7: Blue Hat — Synthesis
        print("Phase 7: Blue Hat — Synthesizing all perspectives...")
        span = create_span("stage:blue_hat_synthesis", {"hat_count": len(result.hat_outputs)})
        try:
            result.synthesis = await self._blue_hat_synthesize(question, result.hat_outputs)
            end_span(span, output="synthesis complete")
        except Exception:
            end_span(span, error="blue_hat_synthesis failed")
            raise

        return result

    async def _blue_hat_frame(self, question: str) -> str:
        """Phase 1: Blue Hat framing (orchestrator only, Haiku)."""
        response = await llm_complete(
            self.client,
            model=self.orchestration_model,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": BLUE_HAT_FRAMING_PROMPT.format(question=question),
            }],
            agent_name="blue_hat_framing",
        )
        return extract_text(response)

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
                response = await llm_complete(
                    self.client,
                    model=self.thinking_model,
                    max_tokens=self.thinking_budget + 4096,
                    thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
                    messages=messages,
                    agent_name=agent["name"],
                )
            else:
                response = await llm_complete(
                    self.client,
                    model=self.thinking_model,
                    max_tokens=512,
                    messages=messages,
                    agent_name=agent["name"],
                )
            return agent["name"], extract_text(response)

        results = await asyncio.gather(
            *(query_agent(agent) for agent in self.agents),
            return_exceptions=True,
        )
        results = filter_exceptions(results, label="p28_six_hats")
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

        response = await llm_complete(
            self.client,
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
            agent_name="synthesis",
        )
        return extract_text(response)


