"""Async session factory."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ce_db.engine import get_engine

_session_factory: async_sessionmaker[AsyncSession] | None = None


def async_session_factory() -> async_sessionmaker[AsyncSession] | None:
    """Get or create session factory. Returns None if no engine."""
    global _session_factory
    if _session_factory is not None:
        return _session_factory
    engine = get_engine()
    if engine is None:
        return None
    _session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for DB sessions. Raises if DB unavailable."""
    factory = async_session_factory()
    if factory is None:
        raise RuntimeError("Database not configured")
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
