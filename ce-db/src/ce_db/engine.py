"""Async SQLAlchemy engine from DATABASE_URL or POSTGRES_* vars."""
from __future__ import annotations

import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

from ce_shared.env import find_and_load_dotenv

logger = logging.getLogger(__name__)

_env_loaded = False


def _ensure_env() -> None:
    """Load .env once on first use, not at import time."""
    global _env_loaded
    if not _env_loaded:
        find_and_load_dotenv()
        _env_loaded = True


def _build_database_url() -> str:
    """Construct DATABASE_URL from env vars.

    Checks DATABASE_URL first as an override, then builds from individual
    POSTGRES_* vars. No hardcoded fallback credentials.
    """
    _ensure_env()
    explicit = os.environ.get("DATABASE_URL")
    if explicit:
        return explicit

    user = os.environ.get("POSTGRES_USER", "ce")
    password = os.environ.get("POSTGRES_PASSWORD", "")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "ce_platform")

    if not password:
        logger.warning("POSTGRES_PASSWORD not set; database connection may fail")

    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


DATABASE_URL: str = ""

_engine: AsyncEngine | None = None


def get_database_url() -> str:
    """Return the database URL, building it on first call."""
    global DATABASE_URL
    if not DATABASE_URL:
        DATABASE_URL = _build_database_url()
    return DATABASE_URL


def get_engine() -> AsyncEngine | None:
    """Get or create async engine. Returns None if DATABASE_URL is empty."""
    global _engine
    url = get_database_url()
    if not url:
        return None
    if _engine is None:
        try:
            _engine = create_async_engine(url, echo=False, pool_size=5)
        except Exception as e:
            logger.warning("Failed to create DB engine: %s", e)
            return None
    return _engine
