"""Evaluation models."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ce_db.models.core import Base


class EvalRun(Base):
    __tablename__ = "eval_runs"
    __table_args__ = (
        Index("ix_eval_runs_run_id", "run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("runs.id", ondelete="SET NULL"), nullable=True
    )
    rubric_name: Mapped[str] = mapped_column(String(200))
    judge_backend: Mapped[str] = mapped_column(String(100))
    aggregate_score: Mapped[float] = mapped_column(Float)
    scores_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    question_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
