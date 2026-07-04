"""Protocol learning models — stores run outcomes and aggregated insights."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Float, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ce_db.models.core import Base


class ProtocolInsight(Base):
    """Aggregated learning from past protocol runs."""

    __tablename__ = "protocol_insights"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    protocol_key: Mapped[str] = mapped_column(String(100))
    question_category: Mapped[str] = mapped_column(String(50))
    insight_type: Mapped[str] = mapped_column(String(50))
    insight_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    best_synthesis: Mapped[str | None] = mapped_column(Text, default=None)
    best_score: Mapped[float | None] = mapped_column(Float, default=None)
    computed_at: Mapped[datetime] = mapped_column(default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        UniqueConstraint(
            "protocol_key", "question_category", "insight_type",
            name="uq_insights_lookup",
        ),
        Index(
            "ix_insights_lookup",
            "protocol_key", "question_category", "insight_type",
        ),
    )


class RunLearning(Base):
    """Per-run learning record for aggregation into insights."""

    __tablename__ = "run_learnings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[str] = mapped_column(String(100))
    protocol_key: Mapped[str] = mapped_column(String(100))
    question_categories: Mapped[list] = mapped_column(JSONB, default=list)
    eval_score: Mapped[float | None] = mapped_column(Float, default=None)
    config_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    synthesis_excerpt: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    __table_args__ = (
        Index("ix_run_learnings_protocol", "protocol_key"),
        Index("ix_run_learnings_score", "eval_score"),
        Index(
            "ix_run_learnings_categories", "question_categories",
            postgresql_using="gin",
        ),
    )
