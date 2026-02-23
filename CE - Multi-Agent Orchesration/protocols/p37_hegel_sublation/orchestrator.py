"""P37: Hegel Sublation Synthesis — Agent-agnostic orchestrator.

Thesis → Antithesis → Sublation (aufheben): preserve, negate, transcend.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import anthropic

from .prompts import (
    ANTITHESIS_PROMPT,
    SUBLATION_PROMPT,
    THESIS_PROMPT,
)


@dataclass
class SublationResult:
    question: str
    thesis: str = ""
    antithesis: str = ""
    sublation: str = ""
    preserves: str = ""
    negates: str = ""
    transcends: str = ""
    synthesis: str = ""


class SublationOrchestrator:
    """Runs the 3-phase Hegel Sublation protocol."""

    def __init__(
        self,
        agents: list[dict] | None = None,
        thinking_model: str = "claude-opus-4-6",
        orchestration_model: str = "claude-haiku-4-5-20251001",
        thinking_budget: int = 10_000,
    ):
        """
        Args:
            agents: Not used — this protocol uses internal role agents.
                    Accepted for interface compatibility.
            thinking_model: Model for all three phases (thesis, antithesis, sublation).
            orchestration_model: Not used — all phases require deep reasoning.
            thinking_budget: Token budget for extended thinking on Opus calls.
        """
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    async def run(
        self,
        question: str,
        position_a: str | None = None,
        position_b: str | None = None,
    ) -> SublationResult:
        """Execute the full Hegel Sublation protocol."""
        result = SublationResult(question=question)

        # Derive positions if not explicitly provided
        if not position_a:
            position_a = "The affirmative position on the question"
        if not position_b:
            position_b = "The opposing position on the question"

        # Phase 1: Thesis
        print("Phase 1: Generating Thesis...")
        result.thesis = await self._generate_thesis(question, position_a)

        # Phase 2: Antithesis
        print("Phase 2: Generating Antithesis...")
        result.antithesis = await self._generate_antithesis(
            question, position_b, result.thesis
        )

        # Phase 3: Sublation
        print("Phase 3: Performing Sublation (aufheben)...")
        sublation_text = await self._generate_sublation(
            question, result.thesis, result.antithesis
        )
        result.sublation = sublation_text

        # Extract sections from sublation output
        result.preserves = _extract_section(sublation_text, "Preserved from Thesis", "Preserved from Antithesis", "Negated from Thesis")
        result.negates = _extract_section(sublation_text, "Negated from Thesis", "Negated from Antithesis", "The Transcendent Synthesis")
        result.transcends = _extract_section(sublation_text, "The Transcendent Synthesis", "Final Synthesis Statement")
        result.synthesis = _extract_section(sublation_text, "Final Synthesis Statement")

        return result

    async def _generate_thesis(self, question: str, position_a: str) -> str:
        """Phase 1: Present the strongest case for Position A."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            system="You are a dialectical philosopher tasked with presenting the Thesis position with full conviction.",
            messages=[{
                "role": "user",
                "content": THESIS_PROMPT.format(
                    question=question, position_a=position_a
                ),
            }],
        )
        return _extract_text(response)

    async def _generate_antithesis(
        self, question: str, position_b: str, thesis: str
    ) -> str:
        """Phase 2: Present the strongest case for Position B."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            system="You are a dialectical philosopher tasked with presenting the Antithesis position with full conviction.",
            messages=[{
                "role": "user",
                "content": ANTITHESIS_PROMPT.format(
                    question=question, position_b=position_b, thesis=thesis
                ),
            }],
        )
        return _extract_text(response)

    async def _generate_sublation(
        self, question: str, thesis: str, antithesis: str
    ) -> str:
        """Phase 3: Perform aufheben — preserve, negate, transcend."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            system="You are a master dialectician performing Hegelian sublation. You must preserve, negate, and transcend both positions.",
            messages=[{
                "role": "user",
                "content": SUBLATION_PROMPT.format(
                    question=question, thesis=thesis, antithesis=antithesis
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


def _extract_section(text: str, start_heading: str, *end_headings: str) -> str:
    """Extract content between markdown section headings."""
    start_marker = f"## {start_heading}"
    start_idx = text.find(start_marker)
    if start_idx == -1:
        return ""
    start_idx += len(start_marker)

    # Find the earliest end marker
    end_idx = len(text)
    for heading in end_headings:
        marker = f"## {heading}"
        idx = text.find(marker, start_idx)
        if idx != -1 and idx < end_idx:
            end_idx = idx

    return text[start_idx:end_idx].strip()
