"""Tests for the multi-agent evaluation framework."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from csuite.evaluation.benchmark import (
    ALL_ROLE_SYSTEM_PROMPT,
    BENCHMARK_QUESTIONS,
    BenchmarkResult,
    BenchmarkRunner,
    ModeResult,
    _estimate_cost,
)
from csuite.evaluation.judge import (
    JudgeResult,
    _parse_judge_response,
    _strip_metadata,
)
from csuite.evaluation.report import EvaluationReport

# ============================================================================
# Benchmark tests
# ============================================================================


class TestBenchmarkQuestions:
    def test_fifteen_questions_defined(self):
        assert len(BENCHMARK_QUESTIONS) == 15

    def test_all_questions_have_required_fields(self):
        for q in BENCHMARK_QUESTIONS:
            assert "id" in q
            assert "text" in q
            assert "expected_tensions" in q
            assert len(q["text"]) > 20

    def test_question_ids_unique(self):
        ids = [q["id"] for q in BENCHMARK_QUESTIONS]
        assert len(ids) == len(set(ids))


class TestModeResult:
    def test_mode_result_creation(self):
        mr = ModeResult(
            mode="single",
            question_id="pricing",
            output_text="test output",
            cost=0.15,
            duration_seconds=5.0,
        )
        assert mr.mode == "single"
        assert mr.cost == 0.15

    def test_mode_result_defaults(self):
        mr = ModeResult(mode="debate", question_id="plg", output_text="")
        assert mr.cost == 0.0
        assert mr.trace_metrics == {}


class TestCostEstimation:
    def test_opus_pricing(self):
        cost = _estimate_cost("claude-opus-4-6", 1000, 500)
        expected = (1000 * 5.0 + 500 * 25.0) / 1_000_000
        assert abs(cost - expected) < 0.0001

    def test_haiku_pricing(self):
        cost = _estimate_cost("claude-haiku-4-5-20251001", 1000, 500)
        expected = (1000 * 1.0 + 500 * 5.0) / 1_000_000
        assert abs(cost - expected) < 0.0001


class TestAllRolePrompt:
    def test_all_roles_mentioned(self):
        for role in ["CEO", "CFO", "CTO", "CMO", "COO", "CPO", "CRO"]:
            assert role in ALL_ROLE_SYSTEM_PROMPT


class TestBenchmarkRunner:
    @pytest.mark.asyncio
    async def test_run_single_mocked(self):
        runner = BenchmarkRunner(silent=True)
        with patch("csuite.evaluation.benchmark.AGENT_CLASSES") as mock_classes:
            mock_agent = MagicMock()
            mock_agent.chat = AsyncMock(return_value="mock response")
            mock_classes.__getitem__ = MagicMock(return_value=lambda **kw: mock_agent)

            result = await runner.run_single("test question", "test_q", "ceo")
            assert result.mode == "single"
            assert result.output_text == "mock response"

    @pytest.mark.asyncio
    async def test_run_single_with_context_mocked(self):
        runner = BenchmarkRunner(silent=True)
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="context response")]
        mock_response.model = "claude-opus-4-6"
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 200

        with patch("csuite.evaluation.benchmark.anthropic.Anthropic") as mock_client:
            mock_client.return_value.messages.create.return_value = mock_response
            result = await runner.run_single_with_context("test", "test_q")
            assert result.mode == "context"
            assert result.output_text == "context response"


# ============================================================================
# Judge tests
# ============================================================================


class TestStripMetadata:
    def test_removes_debate_mode(self):
        text = "This debate mode analysis shows..."
        assert "debate mode" not in _strip_metadata(text)

    def test_removes_constraint_counts(self):
        text = "Found Constraints: 26 across agents"
        assert "Constraints: 26" not in _strip_metadata(text)

    def test_removes_debate_id(self):
        text = "Debate ID: abc123xyz more text"
        assert "abc123xyz" not in _strip_metadata(text)


def _all_dims(score: int) -> dict[str, int]:
    """Build a dict of all 7 dimensions set to the same score."""
    return {
        "specificity": score, "internal_consistency": score,
        "tension_surfacing": score, "constraint_awareness": score,
        "actionability": score, "reasoning_depth": score,
        "completeness": score,
    }


class TestParseJudgeResponse:
    def test_valid_json(self):
        import json as _json
        data = {
            "scores": {
                "Response A": _all_dims(4),
                "Response B": _all_dims(3),
            },
            "ranking": ["Response A", "Response B"],
            "reasoning": "A was more specific.",
        }
        raw = _json.dumps(data)
        label_map = {
            "Response A": "debate",
            "Response B": "single",
        }
        result = _parse_judge_response(raw, label_map)

        assert "debate" in result.scores
        assert "single" in result.scores
        assert result.scores["debate"]["specificity"] == 4
        assert result.ranking == ["debate", "single"]
        assert "specific" in result.judge_reasoning

    def test_json_in_code_block(self):
        raw = (
            '```json\n'
            '{"scores": {}, "ranking": [], "reasoning": "test"}'
            '\n```'
        )
        result = _parse_judge_response(raw, {})
        assert result.judge_reasoning == "test"

    def test_invalid_json(self):
        result = _parse_judge_response("not json at all", {})
        assert "Failed to parse" in result.judge_reasoning


class TestBlindJudgeRandomization:
    def test_labels_assigned(self):
        """Verify that label_to_mode mapping works."""
        import json as _json
        label_map = {
            "Response A": "single",
            "Response B": "debate",
            "Response C": "negotiate",
        }
        data = {
            "scores": {
                "Response A": _all_dims(3),
                "Response B": _all_dims(4),
                "Response C": _all_dims(5),
            },
            "ranking": ["Response C", "Response B", "Response A"],
            "reasoning": "C best.",
        }
        raw = _json.dumps(data)
        result = _parse_judge_response(raw, label_map)
        assert result.ranking == ["negotiate", "debate", "single"]


# ============================================================================
# Report tests
# ============================================================================


class TestEvaluationReport:
    def _make_test_data(self):
        benchmark = BenchmarkResult(results={
            "pricing": {
                "single": ModeResult(
                    mode="single", question_id="pricing", output_text="x",
                    cost=0.15, duration_seconds=5.0,
                ),
                "debate": ModeResult(
                    mode="debate", question_id="pricing", output_text="y",
                    cost=1.00, duration_seconds=30.0,
                    trace_metrics={"node_count": 12, "revision_count": 3, "constraint_count": 0},
                ),
            },
        })
        judge_results = {
            "pricing": JudgeResult(
                scores={
                    "single": {d: 3.0 for d in ["specificity", "internal_consistency",
                        "tension_surfacing", "constraint_awareness", "actionability",
                        "reasoning_depth", "completeness"]},
                    "debate": {d: 4.0 for d in ["specificity", "internal_consistency",
                        "tension_surfacing", "constraint_awareness", "actionability",
                        "reasoning_depth", "completeness"]},
                },
                ranking=["debate", "single"],
                judge_reasoning="Debate was better.",
            ),
        }
        return benchmark, judge_results

    def test_render_produces_markdown(self):
        benchmark, judge_results = self._make_test_data()
        report = EvaluationReport()
        md = report.render(benchmark, judge_results)
        assert "# Multi-Agent Evaluation Report" in md
        assert "Score Table" in md
        assert "Cost Efficiency" in md

    def test_render_includes_structural_metrics(self):
        benchmark, judge_results = self._make_test_data()
        report = EvaluationReport()
        md = report.render(benchmark, judge_results)
        assert "Structural Metrics" in md
        assert "12" in md  # node_count

    def test_render_includes_ranking(self):
        benchmark, judge_results = self._make_test_data()
        report = EvaluationReport()
        md = report.render(benchmark, judge_results)
        assert "Forced Ranking" in md

    def test_render_includes_methodology(self):
        benchmark, judge_results = self._make_test_data()
        report = EvaluationReport()
        md = report.render(benchmark, judge_results)
        assert "Methodology" in md
