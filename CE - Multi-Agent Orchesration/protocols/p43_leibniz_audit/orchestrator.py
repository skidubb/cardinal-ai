"""P43: Leibniz Auditable Chain — Agent-agnostic orchestrator.

Decomposes reasoning into independently verifiable steps, then audits each step.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import anthropic

from .prompts import (
    AUDIT_PROMPT,
    DECOMPOSE_PROMPT,
    VERDICT_PROMPT,
)


@dataclass
class AuditChainResult:
    recommendation: str
    reasoning: str
    steps: list[dict] = field(default_factory=list)
    audit_findings: list[dict] = field(default_factory=list)
    verdict: str = ""
    synthesis: str = ""


class AuditChainOrchestrator:
    """Runs the 3-phase Leibniz Auditable Chain protocol."""

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
        self, recommendation: str, reasoning: str
    ) -> AuditChainResult:
        """Execute the full Leibniz Auditable Chain protocol."""
        result = AuditChainResult(
            recommendation=recommendation, reasoning=reasoning
        )

        # Phase 1: Decompose into steps
        print("Phase 1: Decomposing reasoning into verifiable steps...")
        result.steps = await self._decompose(recommendation, reasoning)

        # Phase 2: Audit each step
        print("Phase 2: Auditing each step...")
        result.audit_findings = await self._audit(result.steps)

        # Phase 3: Verdict
        print("Phase 3: Producing verdict...")
        verdict_data = await self._verdict(result.steps, result.audit_findings)
        result.verdict = verdict_data.get("verdict", "OPAQUE")
        result.synthesis = verdict_data.get("synthesis", "")

        return result

    async def _decompose(
        self, recommendation: str, reasoning: str
    ) -> list[dict]:
        """Phase 1: Decompose reasoning into independently verifiable steps."""
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": DECOMPOSE_PROMPT.format(
                    recommendation=recommendation, reasoning=reasoning
                ),
            }],
        )
        text = _extract_text(response)
        return _parse_json_array(text)

    async def _audit(self, steps: list[dict]) -> list[dict]:
        """Phase 2: Audit each decomposed step."""
        steps_json = json.dumps(steps, indent=2)
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{
                "role": "user",
                "content": AUDIT_PROMPT.format(steps_json=steps_json),
            }],
        )
        text = _extract_text(response)
        return _parse_json_array(text)

    async def _verdict(
        self, steps: list[dict], findings: list[dict]
    ) -> dict:
        """Phase 3: Produce final verdict."""
        steps_json = json.dumps(steps, indent=2)
        findings_json = json.dumps(findings, indent=2)
        response = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": VERDICT_PROMPT.format(
                    steps_json=steps_json, findings_json=findings_json
                ),
            }],
        )
        text = response.content[0].text
        return _parse_json_object(text)


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
