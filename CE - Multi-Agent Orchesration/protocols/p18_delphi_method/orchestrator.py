"""P18: Delphi Method — Orchestrator.

Iterative expert estimation with anonymous feedback and convergence detection.
"""

from __future__ import annotations

import asyncio
import json
import re
import statistics
import time
from dataclasses import dataclass, field
from typing import Any

import anthropic


from .prompts import (
    INITIAL_ESTIMATE_PROMPT,
    REVISION_ESTIMATE_PROMPT,
    FINAL_SYNTHESIS_PROMPT,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Estimate:
    agent: str
    estimate: float
    confidence_low: float
    confidence_high: float
    reasoning: str


@dataclass
class RoundResult:
    round_number: int
    estimates: list[Estimate]
    median: float
    iqr_low: float
    iqr_high: float
    spread: float  # iqr_high - iqr_low


@dataclass
class DelphiResult:
    question: str
    rounds: list[RoundResult]
    converged: bool
    rounds_used: int
    final_estimate: float
    confidence_interval: tuple[float, float]
    reasoning_summary: dict[str, Any]
    timings: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class DelphiOrchestrator:
    """Runs the iterative Delphi estimation protocol."""

    thinking_model: str = "claude-opus-4-6"
    orchestration_model: str = "claude-haiku-4-5-20251001"

    def __init__(
        self,
        agents: list[dict[str, str]],
        *,
        max_rounds: int = 3,
        thinking_model: str | None = None,
        orchestration_model: str | None = None,
        thinking_budget: int = 10_000,
    ) -> None:
        self.agents = agents  # [{"name": ..., "system_prompt": ...}, ...]
        self.max_rounds = max_rounds
        if thinking_model:
            self.thinking_model = thinking_model
        if orchestration_model:
            self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def run(self, question: str) -> DelphiResult:
        timings: dict[str, float] = {}
        rounds: list[RoundResult] = []
        converged = False

        # Round 1 — Independent Estimates
        t0 = time.time()
        estimates = await self._initial_estimates(question)
        round_result = self._compute_stats(1, estimates)
        rounds.append(round_result)
        timings["round_1_estimates"] = time.time() - t0

        # Check convergence after round 1
        converged = self._check_convergence(round_result)

        # Subsequent rounds — Share & Re-estimate
        for rnd in range(2, self.max_rounds + 1):
            if converged:
                break

            t0 = time.time()
            estimates = await self._revision_estimates(
                question, rnd, rounds[-1],
            )
            round_result = self._compute_stats(rnd, estimates)
            rounds.append(round_result)
            timings[f"round_{rnd}_estimates"] = time.time() - t0

            converged = self._check_convergence(round_result)

        # Final synthesis (Haiku)
        t0 = time.time()
        last_round = rounds[-1]
        reasoning_summary = await self._synthesize(
            question, rounds, converged,
        )
        timings["synthesis"] = time.time() - t0

        return DelphiResult(
            question=question,
            rounds=rounds,
            converged=converged,
            rounds_used=len(rounds),
            final_estimate=last_round.median,
            confidence_interval=(last_round.iqr_low, last_round.iqr_high),
            reasoning_summary=reasoning_summary,
            timings=timings,
        )

    # ------------------------------------------------------------------
    # Round 1: Independent Estimates
    # ------------------------------------------------------------------

    async def _initial_estimates(self, question: str) -> list[Estimate]:
        """Each agent provides an independent estimate in parallel (Opus)."""

        async def _one(agent: dict) -> Estimate:
            prompt = INITIAL_ESTIMATE_PROMPT.format(
                question=question,
                agent_name=agent["name"],
                system_prompt=agent["system_prompt"],
            )
            resp = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=self.thinking_budget + 4096,
                thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = self._parse_json_object(self._extract_text(resp))
            return Estimate(
                agent=agent["name"],
                estimate=float(parsed.get("estimate", 0)),
                confidence_low=float(parsed.get("confidence_low", 0)),
                confidence_high=float(parsed.get("confidence_high", 0)),
                reasoning=parsed.get("reasoning", ""),
            )

        results = await asyncio.gather(*[_one(a) for a in self.agents])
        return list(results)

    # ------------------------------------------------------------------
    # Rounds 2+: Revision Estimates
    # ------------------------------------------------------------------

    async def _revision_estimates(
        self,
        question: str,
        round_number: int,
        previous_round: RoundResult,
    ) -> list[Estimate]:
        """Share anonymous stats and reasoning, collect revised estimates (Opus)."""

        # Build anonymous reasoning block (no names)
        anonymous_reasoning = "\n".join(
            f"- Panelist {i + 1} (estimate: {est.estimate}): {est.reasoning}"
            for i, est in enumerate(previous_round.estimates)
        )

        # Map agent name to their previous estimate
        prev_by_agent = {est.agent: est for est in previous_round.estimates}

        async def _one(agent: dict) -> Estimate:
            prev = prev_by_agent.get(agent["name"])
            prompt = REVISION_ESTIMATE_PROMPT.format(
                question=question,
                round_number=round_number,
                agent_name=agent["name"],
                system_prompt=agent["system_prompt"],
                previous_estimate=prev.estimate if prev else "N/A",
                previous_low=prev.confidence_low if prev else "N/A",
                previous_high=prev.confidence_high if prev else "N/A",
                previous_reasoning=prev.reasoning if prev else "N/A",
                previous_round=round_number - 1,
                median=previous_round.median,
                iqr_low=previous_round.iqr_low,
                iqr_high=previous_round.iqr_high,
                spread=previous_round.spread,
                anonymous_reasoning=anonymous_reasoning,
            )
            resp = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=self.thinking_budget + 4096,
                thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = self._parse_json_object(self._extract_text(resp))
            return Estimate(
                agent=agent["name"],
                estimate=float(parsed.get("estimate", 0)),
                confidence_low=float(parsed.get("confidence_low", 0)),
                confidence_high=float(parsed.get("confidence_high", 0)),
                reasoning=parsed.get("reasoning", ""),
            )

        results = await asyncio.gather(*[_one(a) for a in self.agents])
        return list(results)

    # ------------------------------------------------------------------
    # Statistics & Convergence
    # ------------------------------------------------------------------

    def _compute_stats(self, round_number: int, estimates: list[Estimate]) -> RoundResult:
        """Compute median, IQR, and spread for a set of estimates."""
        values = sorted(est.estimate for est in estimates)
        median = statistics.median(values)

        # Compute IQR
        n = len(values)
        if n < 4:
            # With fewer than 4 values, use min/max as bounds
            iqr_low = values[0]
            iqr_high = values[-1]
        else:
            q1_idx = n // 4
            q3_idx = (3 * n) // 4
            iqr_low = values[q1_idx]
            iqr_high = values[q3_idx]

        spread = iqr_high - iqr_low

        return RoundResult(
            round_number=round_number,
            estimates=estimates,
            median=median,
            iqr_low=iqr_low,
            iqr_high=iqr_high,
            spread=spread,
        )

    @staticmethod
    def _check_convergence(round_result: RoundResult) -> bool:
        """Converged if IQR < 15% of median (avoid division by zero)."""
        if round_result.median == 0:
            return round_result.spread == 0
        return abs(round_result.spread / round_result.median) < 0.15

    # ------------------------------------------------------------------
    # Final Synthesis
    # ------------------------------------------------------------------

    async def _synthesize(
        self,
        question: str,
        rounds: list[RoundResult],
        converged: bool,
    ) -> dict[str, Any]:
        """Haiku produces a final reasoning summary."""
        last_round = rounds[-1]
        estimates_block = "\n".join(
            f"- {est.agent}: {est.estimate} (range: {est.confidence_low}–{est.confidence_high})\n"
            f"  Reasoning: {est.reasoning}"
            for est in last_round.estimates
        )

        convergence_note = (
            " The panel converged (IQR < 15% of median)."
            if converged
            else " The panel did NOT converge within the allotted rounds."
        )

        prompt = FINAL_SYNTHESIS_PROMPT.format(
            question=question,
            rounds_used=len(rounds),
            convergence_note=convergence_note,
            estimates_block=estimates_block,
            final_median=last_round.median,
            iqr_low=last_round.iqr_low,
            iqr_high=last_round.iqr_high,
            spread=last_round.spread,
        )

        resp = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._parse_json_object(self._extract_text(resp))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text(response: anthropic.types.Message) -> str:
        parts = []
        for block in response.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "\n".join(parts)

    @staticmethod
    def _parse_json_object(text: str) -> dict:
        """Extract the first JSON object from text."""
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Try to find JSON block
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        # Try to find raw braces
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {}
