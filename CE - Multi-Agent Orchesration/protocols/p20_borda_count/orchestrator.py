"""P20: Borda Count Voting — Orchestrator.

Ranked-choice voting with Borda scoring across multiple agents.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

import anthropic

from .prompts import (
    RANKING_PROMPT,
    TIEBREAK_PROMPT,
    FINAL_REPORT_PROMPT,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Ballot:
    agent: str
    rankings: list[dict[str, Any]]  # [{"rank": 1, "option": "...", "reasoning": "..."}, ...]


@dataclass
class BordaResult:
    question: str
    options: list[str]
    ballots: list[Ballot]
    borda_scores: dict[str, int]
    final_ranking: list[str]
    winner: str
    margin: int
    had_tiebreak: bool
    reasoning_clusters: dict[str, list[str]]
    consensus_score: float
    report: str
    timings: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class BordaCountOrchestrator:
    """Runs the four-phase Borda Count voting protocol."""

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

    async def run(self, question: str, options: list[str]) -> BordaResult:
        timings: dict[str, float] = {}
        k = len(options)

        # Phase 1 — Rank (parallel, Opus with extended thinking)
        t0 = time.time()
        ballots = await self._collect_rankings(question, options)
        timings["phase1_rank"] = time.time() - t0

        # Phase 2 — Score (pure computation, no API call)
        t0 = time.time()
        borda_scores = self._compute_borda_scores(ballots, options, k)
        final_ranking = sorted(options, key=lambda o: borda_scores.get(o, 0), reverse=True)
        timings["phase2_score"] = time.time() - t0

        # Phase 3 — Analyze ties (Condorcet tiebreak if needed)
        t0 = time.time()
        had_tiebreak = False
        if len(final_ranking) >= 2:
            top_score = borda_scores[final_ranking[0]]
            tied_at_top = [o for o in final_ranking if borda_scores[o] == top_score]
            if len(tied_at_top) > 1:
                had_tiebreak = True
                final_ranking = await self._resolve_ties(
                    question, ballots, borda_scores, final_ranking,
                )
        timings["phase3_analyze"] = time.time() - t0

        winner = final_ranking[0] if final_ranking else ""
        margin = 0
        if len(final_ranking) >= 2:
            margin = borda_scores.get(final_ranking[0], 0) - borda_scores.get(final_ranking[1], 0)

        # Phase 4 — Report (Opus)
        t0 = time.time()
        report_data = await self._generate_report(
            question, options, ballots, borda_scores, final_ranking, had_tiebreak,
        )
        timings["phase4_report"] = time.time() - t0

        return BordaResult(
            question=question,
            options=options,
            ballots=ballots,
            borda_scores=borda_scores,
            final_ranking=final_ranking,
            winner=winner,
            margin=margin,
            had_tiebreak=had_tiebreak,
            reasoning_clusters=report_data.get("reasoning_clusters", {}),
            consensus_score=float(report_data.get("consensus_score", 0.0)),
            report=report_data.get("report", ""),
            timings=timings,
        )

    # ------------------------------------------------------------------
    # Phase 1: Collect Rankings
    # ------------------------------------------------------------------

    async def _collect_rankings(
        self, question: str, options: list[str],
    ) -> list[Ballot]:
        """Each agent independently ranks all options (parallel, Opus)."""
        options_block = "\n".join(f"- {opt}" for opt in options)

        async def _one(agent: dict) -> Ballot:
            prompt = RANKING_PROMPT.format(
                question=question,
                agent_name=agent["name"],
                system_prompt=agent["system_prompt"],
                options_block=options_block,
                num_options=len(options),
            )
            resp = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = self._parse_json_object(self._extract_text(resp))
            rankings = parsed.get("rankings", [])
            return Ballot(agent=agent["name"], rankings=rankings)

        ballots = await asyncio.gather(*[_one(a) for a in self.agents])
        return list(ballots)

    # ------------------------------------------------------------------
    # Phase 2: Compute Borda Scores
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_borda_scores(
        ballots: list[Ballot], options: list[str], k: int,
    ) -> dict[str, int]:
        """Borda scoring: 1st = K-1 points, 2nd = K-2, ..., last = 0."""
        scores: dict[str, int] = {opt: 0 for opt in options}
        for ballot in ballots:
            for entry in ballot.rankings:
                rank = entry.get("rank", k)
                option = entry.get("option", "")
                points = max(k - rank, 0)
                if option in scores:
                    scores[option] += points
                else:
                    # Fuzzy match: find closest option
                    matched = _fuzzy_match(option, options)
                    if matched:
                        scores[matched] += points
        return scores

    # ------------------------------------------------------------------
    # Phase 3: Resolve Ties (Condorcet head-to-head)
    # ------------------------------------------------------------------

    async def _resolve_ties(
        self,
        question: str,
        ballots: list[Ballot],
        borda_scores: dict[str, int],
        current_ranking: list[str],
    ) -> list[str]:
        """For groups of tied options, use Condorcet comparison to break ties."""
        # Group options by score
        score_groups: dict[int, list[str]] = {}
        for opt in current_ranking:
            s = borda_scores.get(opt, 0)
            score_groups.setdefault(s, []).append(opt)

        resolved: list[str] = []
        for score in sorted(score_groups.keys(), reverse=True):
            group = score_groups[score]
            if len(group) == 1:
                resolved.extend(group)
            else:
                # Condorcet: count pairwise wins from ballots
                condorcet = self._condorcet_ranking(group, ballots)

                # Use Haiku to produce analysis if needed for the report
                head_to_head_block = self._format_head_to_head(group, ballots)
                tied_options_block = "\n".join(f"- {opt}" for opt in group)
                prompt = TIEBREAK_PROMPT.format(
                    question=question,
                    tied_score=score,
                    tied_options_block=tied_options_block,
                    head_to_head_block=head_to_head_block,
                )
                resp = await self.client.messages.create(
                    model=self.orchestration_model,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                # Use computational Condorcet result (not LLM) for actual ordering
                resolved.extend(condorcet)

        return resolved

    @staticmethod
    def _condorcet_ranking(
        tied_options: list[str], ballots: list[Ballot],
    ) -> list[str]:
        """Rank tied options by pairwise head-to-head wins across ballots."""
        wins: dict[str, int] = {opt: 0 for opt in tied_options}

        for i, a in enumerate(tied_options):
            for b in tied_options[i + 1:]:
                a_wins = 0
                b_wins = 0
                for ballot in ballots:
                    rank_a = _get_rank(ballot, a)
                    rank_b = _get_rank(ballot, b)
                    if rank_a < rank_b:
                        a_wins += 1
                    elif rank_b < rank_a:
                        b_wins += 1
                if a_wins > b_wins:
                    wins[a] += 1
                elif b_wins > a_wins:
                    wins[b] += 1

        return sorted(tied_options, key=lambda o: wins[o], reverse=True)

    @staticmethod
    def _format_head_to_head(
        tied_options: list[str], ballots: list[Ballot],
    ) -> str:
        """Format head-to-head data for the tiebreak prompt."""
        lines = []
        for ballot in ballots:
            agent_ranks = []
            for opt in tied_options:
                rank = _get_rank(ballot, opt)
                agent_ranks.append(f"  {opt}: rank {rank}")
            lines.append(f"{ballot.agent}:\n" + "\n".join(agent_ranks))
        return "\n\n".join(lines)

    # ------------------------------------------------------------------
    # Phase 4: Generate Final Report
    # ------------------------------------------------------------------

    async def _generate_report(
        self,
        question: str,
        options: list[str],
        ballots: list[Ballot],
        borda_scores: dict[str, int],
        final_ranking: list[str],
        had_tiebreak: bool,
    ) -> dict[str, Any]:
        options_block = "\n".join(f"- {opt}" for opt in options)
        ranking_block = "\n".join(
            f"{i + 1}. {opt} — {borda_scores.get(opt, 0)} points"
            for i, opt in enumerate(final_ranking)
        )
        ballots_block = self._format_ballots_block(ballots)
        tiebreak_details = "Condorcet head-to-head comparison was used to break ties." if had_tiebreak else "No tiebreak was needed."

        prompt = FINAL_REPORT_PROMPT.format(
            question=question,
            options_block=options_block,
            ranking_block=ranking_block,
            ballots_block=ballots_block,
            tiebreak_applied="Yes" if had_tiebreak else "No",
            tiebreak_details=tiebreak_details,
        )

        resp = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._parse_json_object(self._extract_text(resp))

    @staticmethod
    def _format_ballots_block(ballots: list[Ballot]) -> str:
        lines = []
        for ballot in ballots:
            agent_lines = [f"### {ballot.agent}"]
            for entry in sorted(ballot.rankings, key=lambda e: e.get("rank", 999)):
                rank = entry.get("rank", "?")
                option = entry.get("option", "?")
                reasoning = entry.get("reasoning", "")
                agent_lines.append(f"  {rank}. {option} — {reasoning}")
            lines.append("\n".join(agent_lines))
        return "\n\n".join(lines)

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


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _get_rank(ballot: Ballot, option: str) -> int:
    """Get the rank an agent assigned to an option, with fuzzy matching."""
    for entry in ballot.rankings:
        if entry.get("option", "") == option:
            return entry.get("rank", 999)
    # Fuzzy fallback
    for entry in ballot.rankings:
        if option.lower() in entry.get("option", "").lower() or entry.get("option", "").lower() in option.lower():
            return entry.get("rank", 999)
    return 999


def _fuzzy_match(candidate: str, options: list[str]) -> str | None:
    """Find the closest matching option for a candidate string."""
    candidate_lower = candidate.strip().lower()
    for opt in options:
        if opt.lower() == candidate_lower:
            return opt
    for opt in options:
        if candidate_lower in opt.lower() or opt.lower() in candidate_lower:
            return opt
    return None
