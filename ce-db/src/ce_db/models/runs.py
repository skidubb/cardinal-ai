"""Run and AgentOutput models."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Float, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ce_db.models.core import Base


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (
        Index("ix_runs_protocol_key", "protocol_key"),
        Index("ix_runs_status", "status"),
        Index("ix_runs_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    protocol_key: Mapped[str] = mapped_column(String(100))
    question: Mapped[str] = mapped_column(Text)
    agent_keys: Mapped[dict] = mapped_column(JSONB, default=list)
    source: Mapped[str] = mapped_column(String(20), default="cli")  # cli, api, ui
    status: Mapped[str] = mapped_column(String(20), default="pending")
    result_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    total_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    langfuse_trace_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(default=lambda: datetime.utcnow())
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.utcnow())

    agent_outputs: Mapped[list[AgentOutput]] = relationship(back_populates="run", cascade="all, delete-orphan")


class AgentOutput(Base):
    __tablename__ = "agent_outputs"
    __table_args__ = (
        Index("ix_agent_outputs_run_id", "run_id"),
        Index("ix_agent_outputs_agent_key", "agent_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    agent_key: Mapped[str] = mapped_column(String(100))
    round_number: Mapped[int] = mapped_column(Integer, default=0)
    output_text: Mapped[str] = mapped_column(Text, default="")
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    run: Mapped[Run] = relationship(back_populates="agent_outputs")
