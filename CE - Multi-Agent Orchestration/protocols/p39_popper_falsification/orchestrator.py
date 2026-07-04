"""P39: Popper Falsification Gate — Agent-agnostic orchestrator.

Post-protocol quality gate: test a recommendation by actively searching
for evidence that it is WRONG.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

import anthropic
from protocols.langfuse_tracing import trace_protocol, create_span, end_span
from protocols.llm import agent_complete, filter_exceptions_aligned, llm_complete, parse_json_array, parse_json_object

from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
import re

from .prompts import (
    EVIDENCE_SEARCH_PROMPT,
    GENERATE_CONDITIONS_PROMPT,
    VERDICT_PROMPT,
)


def _extract_conditions_from_prose(text: str) -> list[str]:
    """Fallback extractor: pull numbered/bulleted items from raw agent prose.

    Each agent is prompted to produce a numbered list of falsification
    conditions. If Haiku's dedup step returns unparseable JSON, we recover by
    parsing the raw agent outputs directly.
    """
    candidates: list[str] = []
    # Numbered lists: "1. ...", "1) ..."
    for match in re.finditer(r"^\s*\d+[\.\)]\s+(.+?)(?=\n\s*\d+[\.\)]|\n\n|\Z)", text, re.DOTALL | re.MULTILINE):
        line = match.group(1).strip().splitlines()[0].strip()
        if 30 <= len(line) <= 400:
            candidates.append(line)
    # Bulleted lists fallback
    if not candidates:
        for match in re.finditer(r"^\s*[-*•]\s+(.+?)$", text, re.MULTILINE):
            line = match.group(1).strip()
            if 30 <= len(line) <= 400:
                candidates.append(line)
    # Dedup while preserving order, take first 5
    seen: set[str] = set()
    out: list[str] = []
    for c in candidates:
        key = c.lower()[:80]
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
        if len(out) >= 5:
            break
    return out


@dataclass
class FalsificationResult:
    recommendation: str
    conditions: list[dict] = field(default_factory=list)
    verdict: str = ""
    verdict_reasoning: str = ""
    synthesis: str = ""


class FalsificationOrchestrator:
    """Runs the 3-phase Popper Falsification Gate with any set of agents."""

    def __init__(
        self,
        agents: list[dict],
        thinking_model: str = THINKING_MODEL,
        orchestration_model: str = ORCHESTRATION_MODEL,
        thinking_budget: int = 10_000,
    ):
        if not agents:
            raise ValueError("At least one agent is required")
        self.agents = agents
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    @trace_protocol("p39_popper_falsification")
    async def run(self, recommendation: str, question: str = "") -> FalsificationResult:
        """Execute the full Popper Falsification Gate."""
        result = FalsificationResult(recommendation=recommendation)
        context = question or "No additional context provided."

        # Phase 1: Generate falsification conditions
        print("Phase 1: Generating falsification conditions...")
        span = create_span("stage:generate_conditions", {"agent_count": len(self.agents)})
        try:
            conditions = await self._generate_conditions(recommendation, context)
            result.conditions = [{"condition": c} for c in conditions]
            end_span(span, output=f"{len(conditions)} conditions generated")
        except Exception:
            end_span(span, error="generate_conditions failed")
            raise

        # Phase 2: Active evidence search (parallel across agents × conditions)
        print("Phase 2: Searching for disconfirming evidence...")
        span = create_span("stage:evidence_search", {"condition_count": len(result.conditions), "agent_count": len(self.agents)})
        try:
            await self._search_evidence(recommendation, context, result.conditions)
            end_span(span, output=f"{len(result.conditions)} conditions searched")
        except Exception:
            end_span(span, error="evidence_search failed")
            raise

        # Phase 3: Verdict
        print("Phase 3: Rendering verdict...")
        span = create_span("stage:verdict", {})
        try:
            await self._render_verdict(recommendation, result)
            end_span(span, output=f"verdict: {result.verdict}")
        except Exception:
            end_span(span, error="verdict failed")
            raise

        return result

    async def _generate_conditions(self, recommendation: str, context: str) -> list[str]:  # noqa: E501
        """Phase 1: Agents generate falsification conditions in parallel."""
        prompt = GENERATE_CONDITIONS_PROMPT.format(
            recommendation=recommendation, context=context
        )

        async def query_agent(agent: dict) -> str:
            response = await agent_complete(
                agent,
                fallback_model=self.thinking_model,
                anthropic_client=self.client,
                thinking_budget=self.thinking_budget,
                max_tokens=self.thinking_budget + 4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return response

        raw_outputs = await asyncio.gather(
            *(query_agent(agent) for agent in self.agents),
            return_exceptions=True,
        )
        raw_outputs = filter_exceptions_aligned(
            raw_outputs,
            label="p39_popper_falsification",
            labels=[a.get("name", "?") for a in self.agents],
        )

        # Combine all agent outputs and deduplicate via orchestration model
        combined = "\n\n".join(
            f"=== {agent['name']} ===\n{output}"
            for agent, output in zip(self.agents, raw_outputs)
            if output is not None
        )
        response = await llm_complete(
            self.client,
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": (
                    "Below are falsification conditions from multiple analysts.\n"
                    "Merge duplicates and return 3-5 unique condition strings, each a "
                    "single sentence.\n\n"
                    "OUTPUT FORMAT — return ONLY a JSON array of strings, no prose, "
                    "no markdown, no wrapping object. Example:\n"
                    '["The commission structure is forced to <10% by regulatory action in Q2 2026",\n'
                    ' "Epic v. Apple injunction extends to all 3rd-party payment flows",\n'
                    ' "DMA Article 6 compliance requires zero-fee sideloading in EU"]\n\n'
                    + combined
                ),
            }],
            agent_name="dedup",
        )
        raw = response
        try:
            parsed = parse_json_array(raw)
        except ValueError:
            # Fallback: if Haiku returned prose, extract numbered/bulleted items
            # from the combined agent output directly.
            parsed = _extract_conditions_from_prose(combined)
        # Normalize to flat list of strings (handles both ["str", ...] and [{"condition": "str"}, ...])
        normalized: list[str] = []
        for item in parsed:
            if isinstance(item, str) and item.strip():
                normalized.append(item.strip())
            elif isinstance(item, dict):
                val = item.get("condition") or item.get("text") or item.get("statement")
                if isinstance(val, str) and val.strip():
                    normalized.append(val.strip())
        if not normalized:
            normalized = _extract_conditions_from_prose(combined)
        return normalized[:5] or ["(no falsification conditions extracted)"]

    async def _search_evidence(
        self, recommendation: str, context: str, conditions: list[dict]
    ) -> None:
        """Phase 2: For each condition, agents search for disconfirming evidence."""

        async def search_condition(condition_dict: dict) -> None:
            condition = condition_dict["condition"]
            prompt = EVIDENCE_SEARCH_PROMPT.format(
                recommendation=recommendation,
                condition=condition,
                context=context,
            )

            async def query_agent(agent: dict) -> str:
                response = await agent_complete(
                    agent,
                    fallback_model=self.thinking_model,
                    anthropic_client=self.client,
                    thinking_budget=self.thinking_budget,
                    max_tokens=self.thinking_budget + 4096,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response

            results = await asyncio.gather(
                *(query_agent(agent) for agent in self.agents),
                return_exceptions=True,
            )
            results = filter_exceptions_aligned(
                results,
                label="p39_popper_falsification",
                labels=[a.get("name", "?") for a in self.agents],
            )
            condition_dict["evidence_for"] = []
            condition_dict["evidence_against"] = []
            condition_dict["assessment"] = ""
            condition_dict["agent_analyses"] = {
                agent["name"]: result
                for agent, result in zip(self.agents, results)
                if result is not None
            }

        await asyncio.gather(*(search_condition(c) for c in conditions), return_exceptions=True)

    async def _render_verdict(
        self, recommendation: str, result: FalsificationResult
    ) -> None:
        """Phase 3: Judge renders verdict using orchestration model."""
        conditions_evidence = json.dumps(
            [
                {
                    "condition": c["condition"],
                    "agent_analyses": c.get("agent_analyses", {}),
                }
                for c in result.conditions
            ],
            indent=2,
        )
        response = await llm_complete(
            self.client,
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": VERDICT_PROMPT.format(
                    recommendation=recommendation,
                    conditions_evidence=conditions_evidence,
                ),
            }],
            agent_name="verdict",
        )
        data = parse_json_object(response)

        # Update conditions with verdict info
        for verdict_cond in data.get("conditions", []):
            for cond in result.conditions:
                if cond["condition"] == verdict_cond.get("condition"):
                    cond["activated"] = verdict_cond.get("activated", False)
                    cond["reasoning"] = verdict_cond.get("reasoning", "")
                    break

        result.verdict = data.get("verdict", "UNKNOWN")
        result.verdict_reasoning = data.get("verdict_reasoning", "")
        result.synthesis = data.get("synthesis", "")





