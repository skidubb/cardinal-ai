"""Integration test for the judge-parse-aggregate pipeline (no API calls)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from ce_evals.core.judge import BlindJudge, _aggregate_results, _parse_judge_response
from ce_evals.core.models import JudgeResult
from ce_evals.core.rubric import Rubric


def _make_rubric() -> Rubric:
    return Rubric(
        name="test",
        dimensions=[
            {"name": "clarity", "description": "Clear"},
            {"name": "depth", "description": "Deep"},
        ],
        judge_system_prompt="Score on:\n{{dimensions}}",
    )


def _fake_judge_json(label_scores: dict[str, dict[str, float]], ranking: list[str]) -> str:
    return json.dumps({
        "scores": label_scores,
        "ranking": ranking,
        "reasoning": "Test reasoning.",
    })


class TestParseJudgeResponse:
    def test_valid_json(self):
        raw = _fake_judge_json(
            {"Response A": {"clarity": 4, "depth": 3}, "Response B": {"clarity": 2, "depth": 5}},
            ["Response A", "Response B"],
        )
        mapping = {"Response A": "proto_x", "Response B": "proto_y"}
        result = _parse_judge_response(raw, mapping)

        assert result.scores["proto_x"]["clarity"] == 4
        assert result.scores["proto_y"]["depth"] == 5
        assert result.ranking == ["proto_x", "proto_y"]

    def test_invalid_json(self):
        result = _parse_judge_response("no json here", {"Response A": "x"})
        assert "Failed to parse" in result.judge_reasoning

    def test_json_with_surrounding_text(self):
        raw = 'Here is my evaluation:\n' + _fake_judge_json(
            {"Response A": {"clarity": 5}}, ["Response A"]
        ) + "\nThat's my analysis."
        result = _parse_judge_response(raw, {"Response A": "proto_a"})
        assert result.scores["proto_a"]["clarity"] == 5


class TestAggregateResults:
    def test_single_judge(self):
        jr = JudgeResult(
            scores={"a": {"clarity": 4.0}, "b": {"clarity": 2.0}},
            ranking=["a", "b"],
            judge_model="m1",
        )
        agg = _aggregate_results([jr], {"Response A": "a", "Response B": "b"})
        assert agg.scores["a"]["clarity"] == 4.0
        assert agg.ranking[0] == "a"

    def test_multi_judge_averaging(self):
        jr1 = JudgeResult(
            scores={"a": {"clarity": 5.0}, "b": {"clarity": 3.0}},
            ranking=["a", "b"],
            judge_model="m1",
        )
        jr2 = JudgeResult(
            scores={"a": {"clarity": 3.0}, "b": {"clarity": 5.0}},
            ranking=["b", "a"],
            judge_model="m2",
        )
        agg = _aggregate_results([jr1, jr2], {})
        assert agg.scores["a"]["clarity"] == 4.0
        assert agg.scores["b"]["clarity"] == 4.0

    def test_no_valid_results(self):
        jr = JudgeResult(judge_model="m1", judge_reasoning="Backend error")
        agg = _aggregate_results([jr], {"Response A": "a"})
        assert "No valid" in agg.judge_reasoning


class TestBlindJudgeEndToEnd:
    """Full pipeline test with mocked backends."""

    @patch("ce_evals.core.judge.get_backend")
    @patch("ce_evals.core.judge.get_settings")
    def test_full_pipeline(self, mock_settings, mock_get_backend):
        mock_settings.return_value = MagicMock(judge_models=["mock-model"])

        # Mock backend returns valid judge JSON
        mock_backend = MagicMock()
        mock_backend.call.return_value = (
            _fake_judge_json(
                {"Response A": {"clarity": 4, "depth": 3}, "Response B": {"clarity": 5, "depth": 4}},
                ["Response B", "Response A"],
            ),
            100,  # input tokens
            200,  # output tokens
        )
        mock_get_backend.return_value = mock_backend

        rubric = _make_rubric()
        judge = BlindJudge(rubric, judge_models=["mock-model"])

        responses = {"proto_x": "Output from protocol X.", "proto_y": "Output from protocol Y."}
        aggregated, per_judge = judge.evaluate(responses, question="Test question?")

        # Should have 1 judge result
        assert len(per_judge) == 1
        assert per_judge[0].judge_model == "mock-model"
        assert per_judge[0].judge_input_tokens == 100

        # Aggregated should have scores for both protocols
        assert len(aggregated.scores) == 2
        assert len(aggregated.ranking) == 2

    @patch("ce_evals.core.judge.get_backend")
    @patch("ce_evals.core.judge.get_settings")
    def test_backend_failure_handled(self, mock_settings, mock_get_backend):
        mock_settings.return_value = MagicMock(judge_models=["fail-model"])
        mock_backend = MagicMock()
        mock_backend.call.side_effect = RuntimeError("API down")
        mock_get_backend.return_value = mock_backend

        rubric = _make_rubric()
        judge = BlindJudge(rubric, judge_models=["fail-model"])

        aggregated, per_judge = judge.evaluate({"a": "text"}, question="Q?")

        assert len(per_judge) == 1
        assert "Backend error" in per_judge[0].judge_reasoning
        assert "No valid" in aggregated.judge_reasoning
