"""Async SQLAlchemy engine from DATABASE_URL."""
from __future__ import annotations

import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://ce:ce_local@localhost:5432/ce_platform",
)

_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine | None:
    """Get or create async engine. Returns None if DATABASE_URL is empty."""
    global _engine
    if not DATABASE_URL:
        return None
    if _engine is None:
        try:
            _engine = create_async_engine(DATABASE_URL, echo=False, pool_size=5)
        except Exception as e:
            logger.warning("Failed to create DB engine: %s", e)
            return None
    return _engine
