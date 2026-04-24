"""Async session factory."""
from __future__ import annotations

from contextlib import asynccontextmanager
import json
import time
import uuid
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ce_db.engine import get_engine

_DEBUG_LOG_PATH = "/Users/scottewalt/Documents/CE - AGENTS/.cursor/debug-a678b6.log"
_DEBUG_SESSION_ID = "a678b6"


def _agent_log(run_id: str, hypothesis_id: str, location: str, message: str, data: dict) -> None:
    try:
        payload = {
            "sessionId": _DEBUG_SESSION_ID,
            "id": f"log_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}",
            "timestamp": int(time.time() * 1000),
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
        }
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, default=str) + "\n")
    except Exception:
        pass

_session_factory: async_sessionmaker[AsyncSession] | None = None


def async_session_factory() -> async_sessionmaker[AsyncSession] | None:
    """Get or create session factory. Returns None if no engine."""
    global _session_factory
    if _session_factory is not None:
        return _session_factory
    engine = get_engine()
    if engine is None:
        # region agent log
        _agent_log(
            "pre-fix",
            "H1,H2,H3,H4",
            "ce-db/src/ce_db/session.py:async_session_factory",
            "ce-db session factory unavailable because engine is None",
            {"session_factory_cached": False},
        )
        # endregion
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
