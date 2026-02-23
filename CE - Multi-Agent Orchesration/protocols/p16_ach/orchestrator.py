"""P16: Analysis of Competing Hypotheses — Orchestrator.

Generate hypotheses, score evidence for/against each, eliminate least supported.
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
    HYPOTHESIS_GENERATION_PROMPT,
    EVIDENCE_LISTING_PROMPT,
    MATRIX_SCORING_PROMPT,
    SENSITIVITY_SYNTHESIS_PROMPT,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Hypothesis:
    id: str
    label: str
    description: str
    inconsistency_count: int = 0
    eliminated: bool = False


@dataclass
class Evidence:
    id: str
    description: str
    diagnostic_score: float = 0.0  # higher = more differentiating


@dataclass
class MatrixCell:
    evidence_id: str
    hypothesis_id: str
    score: str  # C, I, or N
    reasoning: str = ""


@dataclass
class ACHResult:
    question: str
    hypotheses: list[Hypothesis]
    evidence: list[Evidence]
    matrix: list[MatrixCell]
    eliminated: list[Hypothesis]
    surviving: list[Hypothesis]
    synthesis: dict[str, Any]
    timings: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class ACHOrchestrator:
    """Runs the five-phase ACH protocol."""

    thinking_model: str = "claude-opus-4-6"
    orchestration_model: str = "claude-haiku-4-5-20251001"

    def __init__(
        self,
        agents: list[dict[str, str]],
        *,
        thinking_model: str | None = None,
        orchestration_model: str | None = None,
        thinking_budget: int = 10_000,
    ) -> None:
        self.agents = agents  # [{"name": ..., "system_prompt": ...}, ...]
        if thinking_model:
            self.thinking_model = thinking_model
        if orchestration_model:
            self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def run(self, question: str) -> ACHResult:
        timings: dict[str, float] = {}

        # Phase 1 — Generate Hypotheses
        t0 = time.time()
        raw_hypotheses = await self._generate_hypotheses(question)
        hypotheses = self._deduplicate_hypotheses(raw_hypotheses)
        timings["phase1_generate"] = time.time() - t0

        # Phase 2 — List Evidence
        t0 = time.time()
        raw_evidence = await self._list_evidence(question, hypotheses)
        evidence = self._deduplicate_evidence(raw_evidence)
        timings["phase2_evidence"] = time.time() - t0

        # Phase 3 — Build Matrix (Haiku, parallel per evidence×agent)
        t0 = time.time()
        matrix = await self._build_matrix(question, hypotheses, evidence)
        timings["phase3_matrix"] = time.time() - t0

        # Phase 4 — Eliminate
        t0 = time.time()
        eliminated, surviving = self._eliminate(hypotheses, matrix)
        timings["phase4_eliminate"] = time.time() - t0

        # Phase 5 — Sensitivity Analysis + Synthesis
        t0 = time.time()
        diagnostic_evidence = self._compute_diagnosticity(evidence, matrix, hypotheses)
        synthesis = await self._sensitivity_analysis(
            question, surviving, eliminated, evidence, matrix, diagnostic_evidence,
        )
        timings["phase5_synthesis"] = time.time() - t0

        return ACHResult(
            question=question,
            hypotheses=hypotheses,
            evidence=evidence,
            matrix=matrix,
            eliminated=eliminated,
            surviving=surviving,
            synthesis=synthesis,
            timings=timings,
        )

    # ------------------------------------------------------------------
    # Phase 1: Generate Hypotheses
    # ------------------------------------------------------------------

    async def _generate_hypotheses(self, question: str) -> list[dict]:
        """Each agent generates hypotheses in parallel (Opus)."""

        async def _one(agent: dict) -> list[dict]:
            prompt = HYPOTHESIS_GENERATION_PROMPT.format(
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
            return parsed.get("hypotheses", [])

        results = await asyncio.gather(*[_one(a) for a in self.agents])
        return [h for batch in results for h in batch]

    # ------------------------------------------------------------------
    # Phase 2: List Evidence
    # ------------------------------------------------------------------

    async def _list_evidence(self, question: str, hypotheses: list[Hypothesis]) -> list[dict]:
        hyp_block = self._format_hypotheses_block(hypotheses)

        async def _one(agent: dict) -> list[dict]:
            prompt = EVIDENCE_LISTING_PROMPT.format(
                question=question,
                agent_name=agent["name"],
                system_prompt=agent["system_prompt"],
                hypotheses_block=hyp_block,
            )
            resp = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=self.thinking_budget + 4096,
                thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = self._parse_json_object(self._extract_text(resp))
            return parsed.get("evidence", [])

        results = await asyncio.gather(*[_one(a) for a in self.agents])
        return [e for batch in results for e in batch]

    # ------------------------------------------------------------------
    # Phase 3: Build Evidence-Hypothesis Matrix
    # ------------------------------------------------------------------

    async def _build_matrix(
        self,
        question: str,
        hypotheses: list[Hypothesis],
        evidence: list[Evidence],
    ) -> list[MatrixCell]:
        hyp_block = self._format_hypotheses_block(hypotheses)

        async def _score_one(agent: dict, ev: Evidence) -> list[MatrixCell]:
            prompt = MATRIX_SCORING_PROMPT.format(
                question=question,
                evidence_description=f"{ev.id}: {ev.description}",
                hypotheses_block=hyp_block,
            )
            resp = await self.client.messages.create(
                model=self.orchestration_model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = self._parse_json_object(self._extract_text(resp))
            cells = []
            for s in parsed.get("scores", []):
                cells.append(MatrixCell(
                    evidence_id=ev.id,
                    hypothesis_id=s.get("hypothesis_id", ""),
                    score=s.get("score", "N").upper()[:1],
                    reasoning=s.get("reasoning", ""),
                ))
            return cells

        sem = asyncio.Semaphore(4)

        async def _throttled(a, ev):
            async with sem:
                return await _score_one(a, ev)

        tasks = [_throttled(a, ev) for a in self.agents for ev in evidence]
        results = await asyncio.gather(*tasks)
        return [c for batch in results for c in batch]

    # ------------------------------------------------------------------
    # Phase 4: Eliminate
    # ------------------------------------------------------------------

    def _eliminate(
        self,
        hypotheses: list[Hypothesis],
        matrix: list[MatrixCell],
    ) -> tuple[list[Hypothesis], list[Hypothesis]]:
        """Eliminate hypotheses with the most Inconsistent scores (majority-vote aggregated)."""
        # Aggregate: majority vote per (evidence_id, hypothesis_id)
        vote_buckets: dict[tuple[str, str], list[str]] = {}
        for cell in matrix:
            key = (cell.evidence_id, cell.hypothesis_id)
            vote_buckets.setdefault(key, []).append(cell.score)

        aggregated: dict[tuple[str, str], str] = {}
        for key, votes in vote_buckets.items():
            counter = Counter(votes)
            aggregated[key] = counter.most_common(1)[0][0]

        # Count inconsistencies per hypothesis
        for h in hypotheses:
            h.inconsistency_count = sum(
                1 for (_, hid), score in aggregated.items()
                if hid == h.id and score == "I"
            )

        # Sort by inconsistency (ascending = best first)
        ranked = sorted(hypotheses, key=lambda h: h.inconsistency_count)

        if len(ranked) <= 1:
            return [], ranked

        # Eliminate hypotheses with significantly more inconsistencies than the best
        max_inconsistency = ranked[-1].inconsistency_count
        min_inconsistency = ranked[0].inconsistency_count

        # Eliminate those whose inconsistency count is at the max AND strictly above the min
        eliminated = []
        surviving = []
        for h in ranked:
            if h.inconsistency_count == max_inconsistency and max_inconsistency > min_inconsistency:
                h.eliminated = True
                eliminated.append(h)
            else:
                surviving.append(h)

        return eliminated, surviving

    # ------------------------------------------------------------------
    # Phase 5: Sensitivity Analysis + Synthesis
    # ------------------------------------------------------------------

    def _compute_diagnosticity(
        self,
        evidence: list[Evidence],
        matrix: list[MatrixCell],
        hypotheses: list[Hypothesis],
    ) -> list[Evidence]:
        """Evidence is diagnostic if its scores vary across hypotheses."""
        vote_buckets: dict[tuple[str, str], list[str]] = {}
        for cell in matrix:
            key = (cell.evidence_id, cell.hypothesis_id)
            vote_buckets.setdefault(key, []).append(cell.score)

        aggregated: dict[tuple[str, str], str] = {}
        for key, votes in vote_buckets.items():
            aggregated[key] = Counter(votes).most_common(1)[0][0]

        for ev in evidence:
            scores_for_ev = [
                aggregated.get((ev.id, h.id), "N") for h in hypotheses
            ]
            unique = set(scores_for_ev)
            # More unique scores = more diagnostic
            ev.diagnostic_score = len(unique) / max(len(scores_for_ev), 1)

        return sorted(evidence, key=lambda e: e.diagnostic_score, reverse=True)

    async def _sensitivity_analysis(
        self,
        question: str,
        surviving: list[Hypothesis],
        eliminated: list[Hypothesis],
        evidence: list[Evidence],
        matrix: list[MatrixCell],
        diagnostic_evidence: list[Evidence],
    ) -> dict[str, Any]:
        surviving_block = "\n".join(
            f"- {h.id}: {h.label} — {h.description} (inconsistencies: {h.inconsistency_count})"
            for h in surviving
        ) or "None"

        eliminated_block = "\n".join(
            f"- {h.id}: {h.label} — {h.description} (inconsistencies: {h.inconsistency_count})"
            for h in eliminated
        ) or "None"

        matrix_block = self._format_matrix_block(evidence, surviving + eliminated, matrix)

        diagnostic_block = "\n".join(
            f"- {ev.id}: {ev.description} (diagnosticity: {ev.diagnostic_score:.2f})"
            for ev in diagnostic_evidence[:5]
        )

        prompt = SENSITIVITY_SYNTHESIS_PROMPT.format(
            question=question,
            surviving_block=surviving_block,
            eliminated_block=eliminated_block,
            matrix_block=matrix_block,
            diagnostic_block=diagnostic_block,
        )

        resp = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
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

    @staticmethod
    def _format_hypotheses_block(hypotheses: list[Hypothesis]) -> str:
        return "\n".join(
            f"- {h.id}: {h.label} — {h.description}" for h in hypotheses
        )

    def _format_matrix_block(
        self,
        evidence: list[Evidence],
        hypotheses: list[Hypothesis],
        matrix: list[MatrixCell],
    ) -> str:
        """Format the aggregated matrix as a text table."""
        # Aggregate via majority vote
        vote_buckets: dict[tuple[str, str], list[str]] = {}
        for cell in matrix:
            key = (cell.evidence_id, cell.hypothesis_id)
            vote_buckets.setdefault(key, []).append(cell.score)

        aggregated: dict[tuple[str, str], str] = {}
        for key, votes in vote_buckets.items():
            aggregated[key] = Counter(votes).most_common(1)[0][0]

        h_ids = [h.id for h in hypotheses]
        header = "Evidence | " + " | ".join(h_ids)
        sep = "-" * len(header)
        rows = []
        for ev in evidence:
            scores = [aggregated.get((ev.id, hid), "?") for hid in h_ids]
            rows.append(f"{ev.id} | " + " | ".join(scores))

        return header + "\n" + sep + "\n" + "\n".join(rows)

    def _deduplicate_hypotheses(self, raw: list[dict]) -> list[Hypothesis]:
        """Deduplicate by label similarity — keep unique ones, re-index."""
        seen_labels: set[str] = set()
        unique: list[Hypothesis] = []
        idx = 1
        for h in raw:
            label = h.get("label", "").strip().lower()
            if label and label not in seen_labels:
                seen_labels.add(label)
                unique.append(Hypothesis(
                    id=f"H{idx}",
                    label=h.get("label", ""),
                    description=h.get("description", ""),
                ))
                idx += 1
        return unique

    def _deduplicate_evidence(self, raw: list[dict]) -> list[Evidence]:
        """Deduplicate evidence items, re-index."""
        seen: set[str] = set()
        unique: list[Evidence] = []
        idx = 1
        for e in raw:
            desc = e.get("description", "").strip().lower()
            if desc and desc not in seen:
                seen.add(desc)
                unique.append(Evidence(
                    id=f"E{idx}",
                    description=e.get("description", ""),
                ))
                idx += 1
        return unique
