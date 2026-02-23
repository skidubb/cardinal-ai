"""Data models for evaluation pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CandidateResult(BaseModel):
    """Output from a single protocol run on a single question."""

    name: str
    output_text: str
    cost: float = 0.0
    duration_seconds: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    metadata: dict = Field(default_factory=dict)


class JudgeResult(BaseModel):
    """Result from blind evaluation."""

    scores: dict[str, dict[str, float]] = Field(default_factory=dict)
    """Keyed by candidate name -> dimension -> score."""
    ranking: list[str] = Field(default_factory=list)
    """Candidates ranked best to worst."""
    judge_reasoning: str = ""
    judge_model: str = ""
    label_to_candidate: dict[str, str] = Field(default_factory=dict)
    """Maps 'Response A' -> actual candidate name."""
    judge_input_tokens: int = 0
    judge_output_tokens: int = 0
    judge_cost: float = 0.0


class EvalSuite(BaseModel):
    """Full evaluation of multiple candidates on a single question."""

    question_id: str
    question_text: str
    candidates: dict[str, CandidateResult] = Field(default_factory=dict)
    judgment: JudgeResult | None = None
    per_judge_results: list[JudgeResult] = Field(default_factory=list)
