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
    async def run(
        self,
        position_a: str,
        position_b: str | None = None,
    ) -> SquareResult:
        """Classify the relationship between two positions.

        API runner path: called with a single `question` argument (mapped to
        `position_a`). When `position_b` is omitted, use Haiku to extract the
        two opposing positions from the question.
        """
        if position_b is None or not position_b.strip():
            position_a, position_b = await self._extract_positions(position_a)

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

    async def _extract_positions(self, question: str) -> tuple[str, str]:
        """Extract two opposing positions from a question via Haiku."""
        prompt = (
            "You will receive a strategic question that compares two positions, "
            "options, or hypotheses. Extract the two positions being compared. "
            "Respond with JSON only: "
            '{"position_a": "...", "position_b": "..."}.\n\n'
            f"QUESTION:\n{question}"
        )
        resp = await llm_complete(
            self.client,
            model=self.orchestration_model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
            agent_name="extract_positions",
        )
        data = parse_json_object(extract_text(resp))
        a = str(data.get("position_a", "")).strip()
        b = str(data.get("position_b", "")).strip()
        if not a:
            a = question.strip()[:120] or "Position A"
        if not b:
            b = "Alternative"
        return a, b
