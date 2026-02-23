"""P19: Vickrey Auction — Orchestrator.

Second-price sealed-bid auction for option selection among multiple agents.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import anthropic

from .prompts import (
    SEALED_BID_PROMPT,
    CALIBRATED_JUSTIFICATION_PROMPT,
    FINAL_ASSESSMENT_PROMPT,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Bid:
    agent: str
    selected_option: str
    confidence: int
    reasoning: str


@dataclass
class VickreyResult:
    question: str
    options: list[str]
    bids: list[Bid]
    winner: str
    winning_option: str
    original_confidence: int
    second_price_confidence: int
    calibrated_justification: str
    bid_distribution: dict[str, list[int]]
    consensus_score: float
    synthesis: dict[str, Any]
    timings: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class VickreyOrchestrator:
    """Runs the four-phase Vickrey Auction protocol."""

    thinking_model: str = "claude-opus-4-6"
    orchestration_model: str = "claude-haiku-4-5-20251001"

    def __init__(
        self,
        agents: list[dict[str, str]],
        *,
        thinking_model: str | None = None,
        orchestration_model: str | None = None,
    ) -> None:
        self.agents = agents  # [{"name": ..., "system_prompt": ...}, ...]
        if thinking_model:
            self.thinking_model = thinking_model
        if orchestration_model:
            self.orchestration_model = orchestration_model
        self.client = anthropic.AsyncAnthropic()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def run(self, question: str, options: list[str]) -> VickreyResult:
        timings: dict[str, float] = {}

        # Phase 1 — Sealed Bidding
        t0 = time.time()
        bids = await self._sealed_bidding(question, options)
        timings["phase1_sealed_bidding"] = time.time() - t0

        # Phase 2 — Reveal & Rank
        t0 = time.time()
        ranked_bids = sorted(bids, key=lambda b: b.confidence, reverse=True)
        winner_bid = ranked_bids[0]
        second_price = ranked_bids[1].confidence if len(ranked_bids) > 1 else winner_bid.confidence
        bid_distribution = self._compute_distribution(bids)
        consensus_score = self._compute_consensus(bids, options)
        timings["phase2_reveal_rank"] = time.time() - t0

        # Phase 3 — Calibrated Justification
        t0 = time.time()
        justification_data = await self._calibrated_justification(
            question, winner_bid, second_price, bids,
        )
        calibrated_justification = justification_data.get("calibrated_justification", "")
        timings["phase3_calibrated_justification"] = time.time() - t0

        # Phase 4 — Final Assessment
        t0 = time.time()
        synthesis = await self._final_assessment(
            question, options, bids, winner_bid, second_price,
            calibrated_justification, bid_distribution,
        )
        timings["phase4_final_assessment"] = time.time() - t0

        return VickreyResult(
            question=question,
            options=options,
            bids=bids,
            winner=winner_bid.agent,
            winning_option=winner_bid.selected_option,
            original_confidence=winner_bid.confidence,
            second_price_confidence=second_price,
            calibrated_justification=calibrated_justification,
            bid_distribution=bid_distribution,
            consensus_score=consensus_score,
            synthesis=synthesis,
            timings=timings,
        )

    # ------------------------------------------------------------------
    # Phase 1: Sealed Bidding
    # ------------------------------------------------------------------

    async def _sealed_bidding(self, question: str, options: list[str]) -> list[Bid]:
        """Each agent independently selects an option and bids confidence (parallel, Opus)."""
        options_block = "\n".join(f"- {opt}" for opt in options)

        async def _one(agent: dict) -> Bid:
            prompt = SEALED_BID_PROMPT.format(
                question=question,
                agent_name=agent["name"],
                system_prompt=agent["system_prompt"],
                options_block=options_block,
            )
            resp = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = self._parse_json_object(self._extract_text(resp))
            return Bid(
                agent=agent["name"],
                selected_option=parsed.get("selected_option", ""),
                confidence=int(parsed.get("confidence", 50)),
                reasoning=parsed.get("reasoning", ""),
            )

        results = await asyncio.gather(*[_one(a) for a in self.agents])
        return list(results)

    # ------------------------------------------------------------------
    # Phase 3: Calibrated Justification
    # ------------------------------------------------------------------

    async def _calibrated_justification(
        self,
        question: str,
        winner_bid: Bid,
        second_price: int,
        bids: list[Bid],
    ) -> dict[str, Any]:
        """Winner justifies at the second-price confidence level (Opus)."""
        bids_block = "\n".join(
            f"- {b.agent}: selected \"{b.selected_option}\" "
            f"(confidence: {b.confidence}/100) — {b.reasoning}"
            for b in bids
        )

        # Find the winning agent's system prompt
        winner_agent = next(
            (a for a in self.agents if a["name"] == winner_bid.agent),
            self.agents[0],
        )

        prompt = CALIBRATED_JUSTIFICATION_PROMPT.format(
            question=question,
            agent_name=winner_bid.agent,
            system_prompt=winner_agent["system_prompt"],
            winning_option=winner_bid.selected_option,
            original_confidence=winner_bid.confidence,
            second_price_confidence=second_price,
            bids_block=bids_block,
        )
        resp = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._parse_json_object(self._extract_text(resp))

    # ------------------------------------------------------------------
    # Phase 4: Final Assessment
    # ------------------------------------------------------------------

    async def _final_assessment(
        self,
        question: str,
        options: list[str],
        bids: list[Bid],
        winner_bid: Bid,
        second_price: int,
        calibrated_justification: str,
        bid_distribution: dict[str, list[int]],
    ) -> dict[str, Any]:
        """Synthesize final assessment (Haiku)."""
        bids_block = "\n".join(
            f"- {b.agent}: selected \"{b.selected_option}\" "
            f"(confidence: {b.confidence}/100) — {b.reasoning}"
            for b in bids
        )

        distribution_block = "\n".join(
            f"- \"{opt}\": {len(confs)} bid(s), confidences: {confs}"
            for opt, confs in bid_distribution.items()
        )

        options_list = ", ".join(f"\"{o}\"" for o in options)

        prompt = FINAL_ASSESSMENT_PROMPT.format(
            question=question,
            options_list=options_list,
            bids_block=bids_block,
            winner=winner_bid.agent,
            winning_option=winner_bid.selected_option,
            original_confidence=winner_bid.confidence,
            second_price_confidence=second_price,
            calibrated_justification=calibrated_justification,
            distribution_block=distribution_block,
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
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {}

    @staticmethod
    def _compute_distribution(bids: list[Bid]) -> dict[str, list[int]]:
        """Group confidence scores by selected option."""
        dist: dict[str, list[int]] = {}
        for b in bids:
            dist.setdefault(b.selected_option, []).append(b.confidence)
        return dist

    @staticmethod
    def _compute_consensus(bids: list[Bid], options: list[str]) -> float:
        """Compute consensus score: 1.0 = all agents chose same option, 0.0 = max divergence."""
        if not bids:
            return 0.0
        counts = Counter(b.selected_option for b in bids)
        max_count = counts.most_common(1)[0][1]
        # Consensus = fraction of agents that chose the most popular option
        return max_count / len(bids)
