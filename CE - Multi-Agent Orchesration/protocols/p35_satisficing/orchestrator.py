"""P35: Simon Satisficing Protocol — Agent-agnostic orchestrator.

Accept the FIRST option that clears "good enough" thresholds. No optimization.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import anthropic

from .prompts import (
    EVALUATE_OPTION_PROMPT,
    GENERATE_OPTION_PROMPT,
    SYNTHESIS_PROMPT,
    THRESHOLD_PROMPT,
)


@dataclass
class SatisficingResult:
    question: str = ""
    criteria: str = ""
    attempts: list[dict] = field(default_factory=list)
    accepted_option: str | None = None
    attempts_count: int = 0
    synthesis: str = ""


class SatisficingOrchestrator:
    """Runs the Simon Satisficing protocol — accept the first adequate option."""

    def __init__(
        self,
        agents: list[dict] | None = None,
        thinking_model: str = "claude-opus-4-6",
        orchestration_model: str = "claude-haiku-4-5-20251001",
        thinking_budget: int = 10_000,
        max_attempts: int = 5,
    ):
        self.agents = agents or []
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.max_attempts = max_attempts
        self.client = anthropic.AsyncAnthropic()

    async def run(self, question: str) -> SatisficingResult:
        """Execute the full Simon Satisficing protocol."""
        result = SatisficingResult(question=question)

        # Phase 1: Define "good enough" thresholds
        print("Phase 1: Defining 'good enough' thresholds...")
        criteria_data = await self._define_thresholds(question)

        if not criteria_data.get("suitable", True):
            result.criteria = criteria_data.get("reason", "Problem not suitable for satisficing.")
            result.synthesis = f"Satisficing not applicable: {result.criteria}"
            return result

        criteria_list = criteria_data.get("criteria", [])
        result.criteria = json.dumps(criteria_list, indent=2)
        criteria_text = "\n".join(
            f"{c['id']}. {c['name']}: {c['description']}" for c in criteria_list
        )

        # Phase 2-3 loop: Generate option, evaluate, accept or reject
        rejections: list[dict] = []
        for attempt_num in range(1, self.max_attempts + 1):
            print(f"Phase 2: Generating option (attempt {attempt_num}/{self.max_attempts})...")
            option_data = await self._generate_option(question, criteria_text, rejections)

            option_text = (
                f"{option_data.get('option_name', 'Unnamed')}: "
                f"{option_data.get('option_description', '')}"
            )

            print(f"Phase 3: Evaluating option against thresholds...")
            eval_data = await self._evaluate_option(question, criteria_text, option_text)

            accepted = eval_data.get("overall", "REJECT") == "ACCEPT"
            attempt_record = {
                "option": option_text,
                "evaluations": json.dumps(eval_data.get("evaluations", []), indent=2),
                "accepted": accepted,
            }
            result.attempts.append(attempt_record)
            result.attempts_count = attempt_num

            if accepted:
                print(f"Option ACCEPTED on attempt {attempt_num}.")
                result.accepted_option = option_text
                break
            else:
                print(f"Option REJECTED on attempt {attempt_num}.")
                failed = [
                    e for e in eval_data.get("evaluations", [])
                    if e.get("verdict") == "FAIL"
                ]
                rejections.append({
                    "option": option_text,
                    "failed_criteria": failed,
                })
        else:
            print(f"Satisficing FAILED after {self.max_attempts} attempts.")

        # Synthesis
        print("Synthesizing final briefing...")
        result.synthesis = await self._synthesize(question, result)

        return result

    async def _define_thresholds(self, question: str) -> dict:
        """Phase 1: Define binary pass/fail criteria."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": THRESHOLD_PROMPT.format(question=question),
            }],
        )
        return _parse_json_object(_extract_text(response))

    async def _generate_option(
        self, question: str, criteria: str, rejections: list[dict]
    ) -> dict:
        """Phase 2: Generate one viable candidate."""
        if rejections:
            rejection_context = "PREVIOUSLY REJECTED OPTIONS (learn from these):\n"
            for i, r in enumerate(rejections, 1):
                failed_names = [f.get("criterion_name", "?") for f in r["failed_criteria"]]
                rejection_context += (
                    f"\n  Attempt {i}: {r['option']}\n"
                    f"  Failed on: {', '.join(failed_names)}\n"
                )
        else:
            rejection_context = "This is the first attempt. No prior rejections."

        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": GENERATE_OPTION_PROMPT.format(
                    question=question,
                    criteria=criteria,
                    rejection_context=rejection_context,
                ),
            }],
        )
        return _parse_json_object(_extract_text(response))

    async def _evaluate_option(
        self, question: str, criteria: str, option: str
    ) -> dict:
        """Phase 3: Evaluate option against thresholds."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": EVALUATE_OPTION_PROMPT.format(
                    question=question,
                    criteria=criteria,
                    option=option,
                ),
            }],
        )
        return _parse_json_object(_extract_text(response))

    async def _synthesize(self, question: str, result: SatisficingResult) -> str:
        """Final synthesis briefing."""
        results_text = json.dumps({
            "criteria": result.criteria,
            "attempts": result.attempts,
            "accepted_option": result.accepted_option,
            "total_attempts": result.attempts_count,
        }, indent=2)

        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": SYNTHESIS_PROMPT.format(
                    question=question,
                    results=results_text,
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
