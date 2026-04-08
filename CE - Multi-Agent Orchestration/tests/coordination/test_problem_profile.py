"""Tests for ProblemProfile schema and classification."""

import math

from coordination.routing.problem_profile import (
    Decomposability,
    GoalClarity,
    ProblemProfile,
    _parse_profile,
    _safe_enum,
    _safe_score,
)


class TestProblemProfile:
    def test_defaults(self):
        p = ProblemProfile()
        assert p.goal_clarity == GoalClarity.AMBIGUOUS
        assert p.goal_clarity_score == 0.5

    def test_to_vector(self):
        p = ProblemProfile()
        v = p.to_vector()
        assert len(v) == 8
        assert all(0.0 <= x <= 1.0 for x in v)

    def test_similarity_identical(self):
        p = ProblemProfile(goal_clarity_score=0.9, evidence_quality_score=0.1)
        assert p.similarity(p) > 0.99

    def test_similarity_different(self):
        p1 = ProblemProfile(goal_clarity_score=1.0, evidence_quality_score=0.0)
        p2 = ProblemProfile(goal_clarity_score=0.0, evidence_quality_score=1.0)
        # These should be less similar
        assert p1.similarity(p2) < p1.similarity(p1)

    def test_similarity_zero_vector(self):
        p1 = ProblemProfile(
            goal_clarity_score=0, evidence_quality_score=0,
            downside_asymmetry_score=0, time_pressure_score=0,
            stakeholder_complexity_score=0, domain_novelty_score=0,
            evaluation_clarity_score=0, decomposability_score=0,
        )
        p2 = ProblemProfile()
        assert p1.similarity(p2) == 0.0


class TestParseProfile:
    def test_valid_json(self):
        raw = '''{"goal_clarity": {"label": "clear", "score": 0.9},
                  "evidence_quality": {"label": "rich", "score": 0.8},
                  "downside_symmetry": {"label": "symmetric", "score": 0.5},
                  "time_pressure": {"label": "urgent", "score": 0.9},
                  "stakeholder_count": {"label": "few", "score": 0.3},
                  "domain_familiarity": {"label": "well_known", "score": 0.2},
                  "output_type": {"label": "decision", "score": 0.8},
                  "evaluation_clarity": {"label": "objective_metric", "score": 0.9},
                  "decomposability": {"label": "naturally_modular", "score": 0.7}}'''
        p = _parse_profile(raw)
        assert p.goal_clarity == GoalClarity.CLEAR
        assert p.goal_clarity_score == 0.9

    def test_invalid_json_returns_defaults(self):
        p = _parse_profile("not json")
        assert p.goal_clarity == GoalClarity.AMBIGUOUS

    def test_markdown_fenced_json(self):
        raw = '```json\n{"goal_clarity": {"label": "clear", "score": 0.8}}\n```'
        p = _parse_profile(raw)
        assert p.goal_clarity == GoalClarity.CLEAR


class TestSafeHelpers:
    def test_safe_enum_valid(self):
        assert _safe_enum(GoalClarity, "clear") == GoalClarity.CLEAR

    def test_safe_enum_invalid(self):
        result = _safe_enum(GoalClarity, "bogus")
        assert result == GoalClarity.CLEAR  # First member

    def test_safe_enum_none(self):
        result = _safe_enum(GoalClarity, None)
        assert result == GoalClarity.CLEAR

    def test_safe_score_valid(self):
        assert _safe_score(0.7) == 0.7

    def test_safe_score_clamped(self):
        assert _safe_score(1.5) == 1.0
        assert _safe_score(-0.5) == 0.0

    def test_safe_score_none(self):
        assert _safe_score(None) == 0.5
