"""P47: Pólya Look-Back Protocol — Agent-agnostic orchestrator.

Post-protocol reflection: evaluates METHOD, not answer.
"""

from __future__ import annotations

from dataclasses import dataclass

import anthropic

from .prompts import (
    GENERALIZATION_PROMPT,
    META_SYNTHESIS_PROMPT,
    METHOD_ANALYSIS_PROMPT,
)


@dataclass
class LookBackResult:
    question: str
    analysis: str
    protocol_used: str
    method_analysis: str = ""
    generalization: str = ""
    routing_rule: str = ""
    synthesis: str = ""


class LookBackOrchestrator:
    """Runs the 3-phase Pólya Look-Back reflection protocol."""

    def __init__(
        self,
        thinking_model: str = "claude-opus-4-6",
        orchestration_model: str = "claude-haiku-4-5-20251001",
        thinking_budget: int = 10_000,
    ):
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    async def run(
        self, question: str, analysis: str, protocol_used: str
    ) -> LookBackResult:
        """Execute the full Pólya Look-Back protocol."""
        result = LookBackResult(
            question=question,
            analysis=analysis,
            protocol_used=protocol_used,
        )

        # Phase 1: Method Analysis
        print("Phase 1: Method Analysis...")
        result.method_analysis = await self._method_analysis(
            question, analysis, protocol_used
        )

        # Phase 2: Generalization
        print("Phase 2: Generalization...")
        result.generalization = await self._generalization(
            question, protocol_used, result.method_analysis
        )

        # Phase 3: Meta-Synthesis — extract routing rule
        print("Phase 3: Meta-Synthesis...")
        full_reflection = (
            f"METHOD ANALYSIS:\n{result.method_analysis}\n\n"
            f"GENERALIZATION:\n{result.generalization}"
        )
        result.routing_rule = await self._meta_synthesis(
            protocol_used, full_reflection
        )

        result.synthesis = (
            f"## Method Analysis\n\n{result.method_analysis}\n\n"
            f"## Generalization\n\n{result.generalization}\n\n"
            f"## Routing Rule\n\n{result.routing_rule}"
        )

        return result

    async def _method_analysis(
        self, question: str, analysis: str, protocol_used: str
    ) -> str:
        """Phase 1: Evaluate protocol fit, efficiency, and surprises."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": METHOD_ANALYSIS_PROMPT.format(
                    question=question,
                    analysis=analysis,
                    protocol_used=protocol_used,
                ),
            }],
        )
        return _extract_text(response)

    async def _generalization(
        self, question: str, protocol_used: str, method_analysis: str
    ) -> str:
        """Phase 2: Identify transferable insights and routing rules."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": GENERALIZATION_PROMPT.format(
                    question=question,
                    protocol_used=protocol_used,
                    method_analysis=method_analysis,
                ),
            }],
        )
        return _extract_text(response)

    async def _meta_synthesis(
        self, protocol_used: str, reflection: str
    ) -> str:
        """Phase 3: Distill into a concise routing rule."""
        response = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": META_SYNTHESIS_PROMPT.format(
                    protocol_used=protocol_used,
                    reflection=reflection,
                ),
            }],
        )
        return response.content[0].text.strip()


def _extract_text(response: anthropic.types.Message) -> str:
    """Extract text from a response that may contain thinking blocks."""
    parts = []
    for block in response.content:
        if hasattr(block, "text"):
            parts.append(block.text)
    return "\n".join(parts)
