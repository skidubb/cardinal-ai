"""P00: Direct LLM Response — no agents, no tools, one completion.

The bottom rung of the router ladder. Used when a question is factual,
mechanical, or trivially answerable without expertise or coordination.
Defaults to the orchestration model (Haiku) — if the question needs Opus
reasoning, the router should escalate to P01 or higher.
"""

from __future__ import annotations

from dataclasses import dataclass

import anthropic
from protocols.langfuse_tracing import trace_protocol, create_span, end_span
from protocols.llm import extract_text, llm_complete

from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from .prompts import DIRECT_SYSTEM_PROMPT


@dataclass
class DirectResult:
    question: str
    response: str = ""


class DirectOrchestrator:
    """Runs a single LLM completion. No agent, no tools, no coordination."""

    def __init__(
        self,
        agents: list[dict] | None = None,
        thinking_model: str = THINKING_MODEL,
        orchestration_model: str = ORCHESTRATION_MODEL,
        thinking_budget: int = 10_000,
    ):
        """
        Args:
            agents: Unused — P00 is agent-less. Accepted for interface
                    consistency with other protocols (api/runner.py passes it).
            thinking_model: Unused. Accepted for signature consistency.
            orchestration_model: The single model used for the completion.
                                 Haiku by default for low cost.
            thinking_budget: Unused. Accepted for signature consistency.
        """
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    @trace_protocol("p00_direct")
    async def run(self, question: str) -> DirectResult:
        """Execute a single direct LLM completion."""
        result = DirectResult(question=question)

        span = create_span("stage:direct_response", {"model": self.orchestration_model})
        try:
            response = await llm_complete(
                self.client,
                model=self.orchestration_model,
                max_tokens=2048,
                system=DIRECT_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": question}],
                agent_name="direct",
            )
            result.response = extract_text(response).strip()
            end_span(span, output="direct response complete")
        except Exception:
            end_span(span, error="direct_response failed")
            raise

        return result
