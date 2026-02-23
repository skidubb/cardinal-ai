"""P30: Llull Combinatorial Association Protocol — Agent-agnostic orchestrator.

Brute-force combination of concept categories, then evaluate for non-obvious connections.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import anthropic

from .prompts import (
    DEFINE_DISKS_PROMPT,
    EVALUATE_COMBINATIONS_PROMPT,
    GENERATE_COMBINATIONS_PROMPT,
    SYNTHESIS_PROMPT,
)


@dataclass
class CombinatorialResult:
    question: str
    disks: list[dict] = field(default_factory=list)
    combinations: str = ""
    evaluations: str = ""
    non_obvious_count: int = 0
    total_count: int = 0
    synthesis: str = ""


class CombinatorialOrchestrator:
    """Runs the 4-phase Llull Combinatorial Association protocol."""

    def __init__(
        self,
        agents: list[dict],
        thinking_model: str = "claude-opus-4-6",
        orchestration_model: str = "claude-haiku-4-5-20251001",
        thinking_budget: int = 10_000,
    ):
        if not agents:
            raise ValueError("At least one agent is required")
        self.agents = agents
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    async def run(self, question: str) -> CombinatorialResult:
        """Execute the full Llull Combinatorial protocol."""
        result = CombinatorialResult(question=question)

        # Phase 1: Define the Disks
        print("Phase 1: Defining concept disks...")
        result.disks = await self._define_disks(question)
        disks_text = self._format_disks(result.disks)
        print(f"  Defined {len(result.disks)} disks with {sum(len(d['elements']) for d in result.disks)} total elements")

        # Phase 2: Generate All Combinations (Generator agent — no judgment)
        print("Phase 2: Generating all combinations (exhaustive, no filtering)...")
        result.combinations = await self._generate_combinations(question, disks_text)

        # Phase 3: Evaluate for Non-Obvious Relevance (Evaluator agent — separate)
        print("Phase 3: Evaluating combinations for non-obvious relevance...")
        result.evaluations = await self._evaluate_combinations(question, result.combinations)
        result.non_obvious_count, result.total_count = self._count_classifications(result.evaluations)
        pct = (result.non_obvious_count / result.total_count * 100) if result.total_count > 0 else 0
        print(f"  {result.non_obvious_count}/{result.total_count} non-obvious ({pct:.0f}%)")

        # Phase 4: Synthesis
        print("Phase 4: Synthesizing insights from non-obvious combinations...")
        result.synthesis = await self._synthesize(question, disks_text, result.evaluations)

        return result

    async def _define_disks(self, question: str) -> list[dict]:
        """Phase 1: Define 2-3 concept categories with elements."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            system=self.agents[0]["system_prompt"],
            messages=[{
                "role": "user",
                "content": DEFINE_DISKS_PROMPT.format(question=question),
            }],
        )
        text = _extract_text(response)
        return _parse_json_array(text)

    async def _generate_combinations(self, question: str, disks_text: str) -> str:
        """Phase 2: Generator agent produces all combinations without judgment."""
        # Use first agent as Generator
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 8192,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            system=self.agents[0]["system_prompt"] + "\n\nYou are acting as the GENERATOR. Your only job is to produce combinations. Do NOT evaluate or filter.",
            messages=[{
                "role": "user",
                "content": GENERATE_COMBINATIONS_PROMPT.format(
                    question=question, disks_text=disks_text
                ),
            }],
        )
        return _extract_text(response)

    async def _evaluate_combinations(self, question: str, combinations: str) -> str:
        """Phase 3: Evaluator agent classifies combinations (separate from Generator)."""
        # Use second agent (or last if only one) as Evaluator for separation
        evaluator = self.agents[1] if len(self.agents) > 1 else self.agents[0]
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 8192,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            system=evaluator["system_prompt"] + "\n\nYou are acting as the EVALUATOR. You judge combinations you did NOT generate. Be rigorous but open to surprise.",
            messages=[{
                "role": "user",
                "content": EVALUATE_COMBINATIONS_PROMPT.format(
                    question=question, combinations=combinations
                ),
            }],
        )
        return _extract_text(response)

    async def _synthesize(self, question: str, disks_text: str, evaluations: str) -> str:
        """Phase 4: Synthesize non-obvious combinations into actionable insights."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": SYNTHESIS_PROMPT.format(
                    question=question,
                    disks_text=disks_text,
                    evaluations=evaluations,
                ),
            }],
        )
        return _extract_text(response)

    @staticmethod
    def _format_disks(disks: list[dict]) -> str:
        """Format disks for inclusion in prompts."""
        lines = []
        for i, disk in enumerate(disks):
            name = disk.get("category_name", f"Disk {chr(65 + i)}")
            elements = ", ".join(disk.get("elements", []))
            lines.append(f"Disk {chr(65 + i)} ({name}): {elements}")
        return "\n".join(lines)

    @staticmethod
    def _count_classifications(evaluations: str) -> tuple[int, int]:
        """Count (N) non-obvious and total classified combinations."""
        non_obvious = len(re.findall(r"\(N\)", evaluations))
        standard = len(re.findall(r"\(S\)", evaluations))
        irrelevant = len(re.findall(r"\(I\)", evaluations))
        total = non_obvious + standard + irrelevant
        return non_obvious, total


def _extract_text(response: anthropic.types.Message) -> str:
    """Extract text from a response that may contain thinking blocks."""
    parts = []
    for block in response.content:
        if hasattr(block, "text"):
            parts.append(block.text)
    return "\n".join(parts)


def _parse_json_array(text: str) -> list[dict]:
    """Extract a JSON array from LLM output that may contain markdown fences."""
    text = text.strip()
    if "```" in text:
        match = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
    if not text.startswith("["):
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            text = text[start:end + 1]
    return json.loads(text)
