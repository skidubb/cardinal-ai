"""P42: Aristotle Square of Opposition — Agent-agnostic orchestrator.

Lightweight classifier that determines the logical relationship between
two positions before routing to the appropriate debate protocol.
"""

from __future__ import annotations

from dataclasses import dataclass

import anthropic
from protocols.langfuse_tracing import trace_protocol, create_span, end_span
from protocols.llm import extract_text, llm_complete, parse_json_object

from .prompts import CLASSIFICATION_PROMPT
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL


@dataclass
class SquareResult:
    position_a: str
    position_b: str
    classification: str = ""
    reasoning: str = ""
    recommended_protocol: str = ""
    routing_rationale: str = ""


class SquareOrchestrator:
    """Classifies the logical relationship between two positions."""

    def __init__(
        self,
        thinking_model: str = THINKING_MODEL,
        orchestration_model: str = ORCHESTRATION_MODEL,
        thinking_budget: int = 10_000,
    ):
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    @trace_protocol("p42_aristotle_square")
    async def run(self, position_a: str, position_b: str) -> SquareResult:
        """Classify the relationship between two positions."""
        result = SquareResult(position_a=position_a, position_b=position_b)

        print("Classifying logical relationship...")
        span = create_span("stage:classification", {})
        try:
            response = await llm_complete(
                self.client,
                model=self.orchestration_model,
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": CLASSIFICATION_PROMPT.format(
                        position_a=position_a, position_b=position_b
                    ),
                }],
                agent_name="classification",
            )

            data = parse_json_object(extract_text(response))
            end_span(span, output=f"classification={data.get('classification', '')}")
        except Exception:
            end_span(span, error="classification failed")
            raise
        result.classification = data.get("classification", "")
        result.reasoning = data.get("reasoning", "")
        result.recommended_protocol = data.get("recommended_protocol", "")
        result.routing_rationale = data.get("routing_rationale", "")

        return result




