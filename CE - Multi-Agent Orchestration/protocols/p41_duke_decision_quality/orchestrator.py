"""P41: Duke Decision Quality Separation — Orchestrator.

Lightweight process evaluation wrapper. Scores PROCESS quality at decision time,
not outcome quality.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import anthropic
from protocols.llm import extract_text, parse_json_object

from .prompts import ASSESSMENT_PROMPT, PROCESS_EVALUATION_PROMPT
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL


@dataclass
class DecisionQualityResult:
    recommendation: str = ""
    reasoning: str = ""
    scores: dict[str, int] = field(default_factory=dict)
    justifications: dict[str, str] = field(default_factory=dict)
    overall_score: float = 0.0
    assessment: str = ""


DIMENSIONS = [
    "evidence_considered",
    "alternatives_explored",
    "assumptions_tested",
    "bias_checks",
    "calibration",
]


class DecisionQualityOrchestrator:
    """Evaluates decision process quality using the Duke DQ framework."""

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

    async def run(
        self,
        recommendation: str,
        reasoning: str,
        question: str | None = None,
    ) -> DecisionQualityResult:
        """Execute the Duke Decision Quality evaluation."""
        result = DecisionQualityResult(
            recommendation=recommendation,
            reasoning=reasoning,
        )

        # Phase 1: Process Evaluation (thinking model)
        print("Phase 1: Evaluating process quality on 5 dimensions...")
        await self._evaluate_process(result, question)

        # Phase 2: Overall Assessment (orchestration model)
        print("Phase 2: Generating overall assessment...")
        result.assessment = await self._generate_assessment(result)

        return result

    async def _evaluate_process(
        self, result: DecisionQualityResult, question: str | None
    ) -> None:
        """Phase 1: Score the recommendation's process on 5 dimensions."""
        context_section = ""
        if question:
            context_section = f"ORIGINAL QUESTION:\n{question}\n\n"

        prompt = PROCESS_EVALUATION_PROMPT.format(
            recommendation=result.recommendation,
            reasoning=result.reasoning,
            context_section=context_section,
        )

        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{"role": "user", "content": prompt}],
        )

        text = extract_text(response)
        data = parse_json_object(text)

        for dim in DIMENSIONS:
            if dim in data:
                result.scores[dim] = data[dim]["score"]
                result.justifications[dim] = data[dim]["justification"]

        if result.scores:
            result.overall_score = sum(result.scores.values()) / len(result.scores)

    async def _generate_assessment(self, result: DecisionQualityResult) -> str:
        """Phase 2: Synthesize scores into a qualitative assessment."""
        scores_text = "\n".join(
            f"- {dim.replace('_', ' ').title()}: {result.scores.get(dim, 0)}/5 — "
            f"{result.justifications.get(dim, 'N/A')}"
            for dim in DIMENSIONS
        )

        prompt = ASSESSMENT_PROMPT.format(
            overall_score=result.overall_score,
            scores_text=scores_text,
        )

        response = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text




