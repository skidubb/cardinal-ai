"""Evaluation models."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ce_db.models.core import Base


class EvalRun(Base):
    __tablename__ = "eval_runs"
    __table_args__ = (
        Index("ix_eval_runs_run_id", "run_id"),
        Index("ix_eval_runs_experiment_key", "experiment_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("runs.id", ondelete="SET NULL"), nullable=True
    )
    experiment_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    rubric_name: Mapped[str] = mapped_column(String(200))
    judge_backend: Mapped[str] = mapped_column(String(100))
    aggregate_score: Mapped[float] = mapped_column(Float)
    scores_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    question_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))


class EvalSample(Base):
    """Per-candidate measurement row for quality economics."""

    __tablename__ = "eval_samples"
    __table_args__ = (
        Index("ix_eval_samples_eval_run_id", "eval_run_id"),
        Index("ix_eval_samples_question_id", "question_id"),
        Index("ix_eval_samples_candidate_name", "candidate_name"),
        Index("ix_eval_samples_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    eval_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("eval_runs.id", ondelete="CASCADE")
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("runs.id", ondelete="SET NULL"), nullable=True
    )
    question_id: Mapped[str] = mapped_column(String(100))
    candidate_name: Mapped[str] = mapped_column(String(200))
    replication_index: Mapped[int] = mapped_column(Integer, default=1)
    aggregate_score: Mapped[float] = mapped_column(Float, default=0.0)
    score_variance: Mapped[float] = mapped_column(Float, default=0.0)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    is_baseline: Mapped[bool] = mapped_column(Boolean, default=False)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    total_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))


class EvalRegression(Base):
    """Precomputed regression deltas against a baseline."""

    __tablename__ = "eval_regressions"
    __table_args__ = (
        Index("ix_eval_regressions_experiment_key", "experiment_key"),
        Index("ix_eval_regressions_candidate_name", "candidate_name"),
        Index("ix_eval_regressions_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    experiment_key: Mapped[str] = mapped_column(String(200))
    question_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    candidate_name: Mapped[str] = mapped_column(String(200))
    baseline_candidate: Mapped[str] = mapped_column(String(200))
    quality_delta: Mapped[float] = mapped_column(Float, default=0.0)
    variance_delta: Mapped[float] = mapped_column(Float, default=0.0)
    cost_per_correct_delta: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(30), default="neutral")
    thresholds_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
