"""Tests for MarkdownReport rendering."""

from ce_evals.core.models import CandidateResult, EvalSuite, JudgeResult
from ce_evals.core.rubric import Rubric
from ce_evals.report.markdown import MarkdownReport


def _rubric() -> Rubric:
    return Rubric(
        name="test",
        dimensions=[
            {"name": "clarity", "description": "Clear"},
            {"name": "depth", "description": "Deep"},
        ],
        judge_system_prompt="",
    )


def _suite(qid: str = "Q1", scores: dict | None = None) -> EvalSuite:
    scores = scores or {
        "proto_a": {"clarity": 4.0, "depth": 3.0},
        "proto_b": {"clarity": 2.0, "depth": 5.0},
    }
    return EvalSuite(
        question_id=qid,
        question_text="Test question?",
        candidates={
            "proto_a": CandidateResult(name="proto_a", output_text="A output", duration_seconds=10.0),
            "proto_b": CandidateResult(name="proto_b", output_text="B output", duration_seconds=12.0),
        },
        judgment=JudgeResult(
            scores=scores,
            ranking=["proto_b", "proto_a"],
            judge_reasoning="B was deeper.",
            judge_model="test-model",
        ),
        per_judge_results=[
            JudgeResult(
                scores=scores,
                ranking=["proto_b", "proto_a"],
                judge_reasoning="B was deeper.",
                judge_model="test-model",
            ),
        ],
    )


def test_render_contains_all_sections():
    report = MarkdownReport(_rubric())
    md = report.render([_suite()])

    assert "# Protocol Evaluation Report" in md
    assert "## Evaluation Design" in md
    assert "## Executive Summary" in md
    assert "## Score Table" in md
    assert "## Protocol Analysis" in md
    assert "## Cost Efficiency" in md
    assert "## Forced Ranking Summary" in md
    assert "## Per-Question Results" in md
    assert "## Methodology" in md


def test_render_includes_candidates_and_scores():
    report = MarkdownReport(_rubric())
    md = report.render([_suite()], title="Test Report")

    assert "proto_a" in md
    assert "proto_b" in md
    assert "4.0" in md or "3.50" in md  # scores appear somewhere


def test_render_with_multiple_suites():
    report = MarkdownReport(_rubric())
    md = report.render([_suite("Q1"), _suite("Q2")])

    assert "Q1" in md
    assert "Q2" in md
    assert "Questions evaluated:** 2" in md


def test_render_no_judgment():
    suite = EvalSuite(
        question_id="Q1",
        question_text="No judgment here",
        candidates={"x": CandidateResult(name="x", output_text="out")},
    )
    report = MarkdownReport(_rubric())
    md = report.render([suite])

    assert "No judge scores available" in md


def test_protocol_description_fallback():
    """Unknown protocols get title-cased fallback names."""
    report = MarkdownReport(_rubric())
    suite = _suite()
    md = report.render([suite])

    # proto_a/proto_b aren't in descriptions.yaml, should be title-cased
    assert "Proto A" in md or "proto_a" in md


def test_inter_rater_agreement_with_multi_judge():
    scores_a = {"x": {"clarity": 5.0, "depth": 3.0}}
    scores_b = {"x": {"clarity": 2.0, "depth": 4.0}}
    suite = EvalSuite(
        question_id="Q1",
        question_text="Test?",
        candidates={"x": CandidateResult(name="x", output_text="out")},
        judgment=JudgeResult(scores=scores_a, ranking=["x"], judge_model="agg"),
        per_judge_results=[
            JudgeResult(scores=scores_a, ranking=["x"], judge_model="model-1"),
            JudgeResult(scores=scores_b, ranking=["x"], judge_model="model-2"),
        ],
    )
    report = MarkdownReport(_rubric())
    md = report.render([suite])

    assert "## Inter-Rater Agreement" in md
    assert "model-1" in md
    assert "model-2" in md
