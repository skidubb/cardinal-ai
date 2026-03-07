"""P29: PMI Enumeration Protocol — Agent-agnostic orchestrator.

Three frame agents (Plus, Minus, Interesting) enumerate independently,
then a synthesis pass integrates the findings.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import anthropic
from protocols.langfuse_tracing import trace_protocol, create_span, end_span
from protocols.llm import extract_text, llm_complete, filter_exceptions

from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from .prompts import (
    INTERESTING_PROMPT,
    MINUS_PROMPT,
    PLUS_PROMPT,
    PROPOSITION_FRAMING_PROMPT,
    SYNTHESIS_PROMPT,
)


@dataclass
class PMIResult:
    question: str
    proposition: str = ""
    plus_items: str = ""
    minus_items: str = ""
    interesting_items: str = ""
    synthesis: str = ""


class PMIOrchestrator:
    """Runs the PMI Enumeration protocol with internally created frame agents."""

    def __init__(
        self,
        agents: list[dict] | None = None,
        thinking_model: str = THINKING_MODEL,
        orchestration_model: str = ORCHESTRATION_MODEL,
        thinking_budget: int = 10_000,
    ):
        """
        Args:
            agents: Unused — PMI creates its own Plus/Minus/Interesting agents.
                    Accepted for interface consistency with other protocols.
            thinking_model: Model for frame enumeration and synthesis.
            orchestration_model: Model for mechanical steps (proposition framing).
            thinking_budget: Token budget for extended thinking on Opus calls.
        """
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    @trace_protocol("p29_pmi_enumeration")
    async def run(self, question: str) -> PMIResult:
        """Execute the full PMI Enumeration protocol."""
        result = PMIResult(question=question)

        # Phase 1: Frame the proposition
        print("Phase 1: Framing the proposition...")
        span = create_span("stage:proposition_framing", {})
        try:
            result.proposition = await self._frame_proposition(question)
            end_span(span, output="proposition framed")
        except Exception:
            end_span(span, error="proposition_framing failed")
            raise

        # Phase 2: Parallel enumeration (Plus, Minus, Interesting)
        print("Phase 2: Parallel enumeration (Plus / Minus / Interesting)...")
        span = create_span("stage:pmi_enumeration", {"frame_count": 3})
        try:
            plus, minus, interesting = await self._enumerate(result.proposition)
            result.plus_items = plus
            result.minus_items = minus
            result.interesting_items = interesting
            end_span(span, output="3 frames enumerated")
        except Exception:
            end_span(span, error="pmi_enumeration failed")
            raise

        # Phase 3: Synthesis
        print("Phase 3: Synthesizing...")
        span = create_span("stage:synthesis", {})
        try:
            result.synthesis = await self._synthesize(result)
            end_span(span, output="synthesis complete")
        except Exception:
            end_span(span, error="synthesis failed")
            raise

        return result

    async def _frame_proposition(self, question: str) -> str:
        """Phase 1: Restate the question as a clear proposition."""
        response = await llm_complete(
            self.client,
            model=self.orchestration_model,
            max_tokens=512,
            messages=[{
                "role": "user",
                "content": PROPOSITION_FRAMING_PROMPT.format(question=question),
            }],
            agent_name="proposition_framing",
        )
        return extract_text(response).strip()

    async def _enumerate(self, proposition: str) -> tuple[str, str, str]:
        """Phase 2: Three frame agents enumerate in parallel."""
        prompts = [
            PLUS_PROMPT.format(proposition=proposition),
            MINUS_PROMPT.format(proposition=proposition),
            INTERESTING_PROMPT.format(proposition=proposition),
        ]

        frame_labels = ["plus", "minus", "interesting"]

        async def query_frame(prompt: str, idx: int) -> str:
            response = await llm_complete(
                self.client,
                model=self.thinking_model,
                max_tokens=self.thinking_budget + 4096,
                thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
                messages=[{"role": "user", "content": prompt}],
                agent_name=frame_labels[idx],
            )
            return extract_text(response)

        results = await asyncio.gather(*(query_frame(p, i) for i, p in enumerate(prompts)), return_exceptions=True)
        results = filter_exceptions(results, label="p29_pmi_enumeration")
        return results[0], results[1], results[2]

    async def _synthesize(self, result: PMIResult) -> str:
        """Phase 3: Synthesize Plus/Minus/Interesting into recommendations."""
        response = await llm_complete(
            self.client,
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": SYNTHESIS_PROMPT.format(
                    proposition=result.proposition,
                    plus_items=result.plus_items,
                    minus_items=result.minus_items,
                    interesting_items=result.interesting_items,
                ),
            }],
            agent_name="synthesis",
        )
        return extract_text(response)


