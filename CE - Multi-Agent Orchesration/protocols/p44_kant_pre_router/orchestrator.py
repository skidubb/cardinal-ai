"""P44: Kant Architectonic Pre-Router — 2-axis question classifier.

Classifies questions by problem type AND Kantian modality to route
to the optimal coordination protocol.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import anthropic

from .prompts import CLASSIFICATION_PROMPT


@dataclass
class KantRouterResult:
    question: str
    problem_type: str = ""
    modality: str = ""
    modality_reasoning: str = ""
    recommended_protocol: str = ""
    routing_rationale: str = ""


class KantRouterOrchestrator:
    """Single-phase classifier: problem type + Kantian modality."""

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

    async def run(self, question: str) -> KantRouterResult:
        """Classify the question and recommend a protocol."""
        result = KantRouterResult(question=question)

        print("Classifying question...")
        response = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": CLASSIFICATION_PROMPT.format(question=question),
            }],
        )

        data = _parse_json_object(response.content[0].text)
        result.problem_type = data.get("problem_type", "")
        result.modality = data.get("modality", "")
        result.modality_reasoning = data.get("modality_reasoning", "")
        result.recommended_protocol = data.get("recommended_protocol", "")
        result.routing_rationale = data.get("routing_rationale", "")

        return result


def _extract_text(response: anthropic.types.Message) -> str:
    """Extract text from a response that may contain thinking blocks."""
    parts = []
    for block in response.content:
        if hasattr(block, "text"):
            parts.append(block.text)
    return "\n".join(parts)


def _parse_json_object(text: str) -> dict:
    """Extract a JSON object from LLM output that may contain markdown fences."""
    text = text.strip()
    if "```" in text:
        match = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end + 1]
    return json.loads(text)
