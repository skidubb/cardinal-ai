"""Tests for Pydantic model serialization."""

from ce_evals.core.models import CandidateResult, EvalSuite, JudgeResult


def test_candidate_result_roundtrip():
    cr = CandidateResult(name="test", output_text="hello", cost=1.5, duration_seconds=10.0)
    data = cr.model_dump()
    restored = CandidateResult.model_validate(data)
    assert restored.name == "test"
    assert restored.cost == 1.5


def test_judge_result_roundtrip():
    jr = JudgeResult(
        scores={"cand_a": {"clarity": 4.0, "depth": 3.0}},
        ranking=["cand_a"],
        judge_model="test-model",
    )
    data = jr.model_dump()
    restored = JudgeResult.model_validate(data)
    assert restored.scores["cand_a"]["clarity"] == 4.0
    assert restored.ranking == ["cand_a"]


def test_eval_suite_roundtrip():
    cr = CandidateResult(name="p1", output_text="out")
    jr = JudgeResult(scores={"p1": {"dim": 5.0}}, ranking=["p1"])
    suite = EvalSuite(
        question_id="Q1",
        question_text="What?",
        candidates={"p1": cr},
        judgment=jr,
    )
    data = suite.model_dump()
    restored = EvalSuite.model_validate(data)
    assert restored.question_id == "Q1"
    assert "p1" in restored.candidates
    assert restored.judgment is not None
    assert restored.judgment.ranking == ["p1"]


def test_eval_suite_no_judgment():
    suite = EvalSuite(question_id="Q2", question_text="Why?")
    data = suite.model_dump()
    restored = EvalSuite.model_validate(data)
    assert restored.judgment is None
    assert restored.candidates == {}
