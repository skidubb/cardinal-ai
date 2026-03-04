"""Core models — Agent registry."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Float, Integer, Boolean, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(100), index=True)
    model: Mapped[str] = mapped_column(String(100))
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tools_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    mcp_servers_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    kb_namespaces_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)
