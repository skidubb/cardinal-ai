"""Tests for walk_shared.selection — salience scoring, promotion, wildcard, pairings."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest


def _make_shallow(agent_key: str, lens_family: str = "systems"):
    from protocols.walk_shared.schemas import ShallowWalkOutput
    return ShallowWalkOutput(
        agent_key=agent_key, agent_name=f"Agent {agent_key}",
        lens_family=lens_family, reframe="r", hidden_variable="h",
        blind_spot="b", testable_implication="t",
    )


def _make_score(agent_key: str, composite: float, cog_dist: float = 5.0):
    from protocols.walk_shared.schemas import SalienceScore
    return SalienceScore(
        agent_key=agent_key, novelty=composite, explanatory_power=composite,
        actionability=composite, cognitive_distance=cog_dist,
        composite=composite, rationale="test",
    )


class TestSelectPromoted:
    def test_selects_top_n_by_composite(self):
        from protocols.walk_shared.selection import select_promoted
        scores = [
            _make_score("a", 9.0),
            _make_score("b", 7.0),
            _make_score("c", 8.0),
            _make_score("d", 6.0),
            _make_score("e", 5.0),
        ]
        promoted = select_promoted(scores, top_n=3)
        assert promoted == ["a", "c", "b"]  # sorted by composite desc

    def test_top_n_exceeds_available(self):
        from protocols.walk_shared.selection import select_promoted
        scores = [_make_score("a", 9.0), _make_score("b", 7.0)]
        promoted = select_promoted(scores, top_n=5)
        assert len(promoted) == 2

    def test_empty_scores(self):
        from protocols.walk_shared.selection import select_promoted
        promoted = select_promoted([], top_n=3)
        assert promoted == []

    def test_include_wildcard(self):
        from protocols.walk_shared.selection import select_promoted
        scores = [
            _make_score("a", 9.0, cog_dist=3.0),
            _make_score("b", 8.0, cog_dist=4.0),
            _make_score("c", 7.0, cog_dist=5.0),
            _make_score("d", 3.0, cog_dist=9.5),  # low composite but high distance
            _make_score("e", 6.0, cog_dist=2.0),
        ]
        promoted = select_promoted(scores, top_n=3, include_wildcard=True)
        # Top 3 by composite: a, b, c. Wildcard should be d (highest cog_dist not already in top)
        assert "d" in promoted
        assert len(promoted) == 4

    def test_wildcard_already_in_top_n(self):
        """If highest cog_dist agent is already promoted, no extra wildcard."""
        from protocols.walk_shared.selection import select_promoted
        scores = [
            _make_score("a", 9.0, cog_dist=9.5),  # top scorer AND highest distance
            _make_score("b", 8.0, cog_dist=4.0),
            _make_score("c", 7.0, cog_dist=5.0),
        ]
        promoted = select_promoted(scores, top_n=3, include_wildcard=True)
        assert len(promoted) == 3  # no extra wildcard needed


class TestBuildCrossExamPairings:
    def test_round_robin(self):
        from protocols.walk_shared.selection import build_cross_exam_pairings
        pairings = build_cross_exam_pairings(["a", "b", "c"])
        assert len(pairings) == 3
        # Each agent challenges exactly one other
        challengers = [p[0] for p in pairings]
        assert set(challengers) == {"a", "b", "c"}
        # No self-examination
        for challenger, target in pairings:
            assert challenger != target

    def test_two_agents(self):
        from protocols.walk_shared.selection import build_cross_exam_pairings
        pairings = build_cross_exam_pairings(["a", "b"])
        assert len(pairings) == 2
        assert ("a", "b") in pairings
        assert ("b", "a") in pairings

    def test_single_agent(self):
        from protocols.walk_shared.selection import build_cross_exam_pairings
        pairings = build_cross_exam_pairings(["a"])
        assert pairings == []

    def test_empty(self):
        from protocols.walk_shared.selection import build_cross_exam_pairings
        assert build_cross_exam_pairings([]) == []


class TestScoreSalience:
    """Integration-level test with mocked LLM."""

    @patch("protocols.walk_shared.selection.llm_complete")
    @patch("protocols.walk_shared.selection.extract_text")
    @patch("protocols.walk_shared.selection.parse_json_object")
    def test_returns_salience_artifact(self, mock_parse, mock_extract, mock_llm):
        from protocols.walk_shared.schemas import FrameArtifact
        from protocols.walk_shared.selection import score_salience

        frame = FrameArtifact(
            question="Q", objective="O", constraints=[], assumptions=[],
            known_dead_ends=[], ambiguity_map=[], unresolved_tensions=[],
        )
        shallow_outputs = [
            _make_shallow("walk-systems", "systems"),
            _make_shallow("walk-poet", "aesthetic"),
        ]

        mock_llm.return_value = AsyncMock()
        mock_extract.return_value = "json"
        mock_parse.return_value = {
            "ranked_outputs": [
                {"agent_key": "walk-poet", "novelty": 9, "explanatory_power": 5, "actionability": 4, "cognitive_distance": 9, "composite": 6.8, "rationale": "Novel metaphor"},
                {"agent_key": "walk-systems", "novelty": 7, "explanatory_power": 8, "actionability": 6, "cognitive_distance": 4, "composite": 6.3, "rationale": "Good systems analysis"},
            ],
            "top_tensions": ["t1"],
            "candidate_hypotheses": ["h1"],
        }

        result = asyncio.run(score_salience(
            shallow_outputs=shallow_outputs,
            frame=frame,
            client=AsyncMock(),
            model="claude-haiku-4-5-20251001",
        ))

        from protocols.walk_shared.schemas import SalienceArtifact
        assert isinstance(result, SalienceArtifact)
        assert len(result.ranked_outputs) == 2
        assert result.ranked_outputs[0].composite >= result.ranked_outputs[1].composite
