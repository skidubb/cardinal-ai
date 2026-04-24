"""Async SQLAlchemy engine from DATABASE_URL or POSTGRES_* vars."""
from __future__ import annotations

import os
import logging
import json
import time
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.engine import make_url

from ce_shared.env import find_and_load_dotenv

logger = logging.getLogger(__name__)
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

_env_loaded = False


def _ensure_env() -> None:
    """Load .env once on first use, not at import time."""
    global _env_loaded
    if not _env_loaded:
        # region agent log
        before = {
            "cwd": os.getcwd(),
            "database_url_present": bool(os.environ.get("DATABASE_URL")),
            "postgres_host_present": bool(os.environ.get("POSTGRES_HOST")),
            "postgres_password_present": bool(os.environ.get("POSTGRES_PASSWORD")),
        }
        # endregion
        loaded_path = find_and_load_dotenv()
        # region agent log
        _agent_log(
            "pre-fix",
            "H1,H3,H4",
            "ce-db/src/ce_db/engine.py:_ensure_env",
            "ce-db env load completed",
            {
                "before": before,
                "loaded_path": str(loaded_path) if loaded_path else None,
                "after": {
                    "database_url_present": bool(os.environ.get("DATABASE_URL")),
                    "postgres_host_present": bool(os.environ.get("POSTGRES_HOST")),
                    "postgres_password_present": bool(os.environ.get("POSTGRES_PASSWORD")),
                },
            },
        )
        # endregion
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
    # region agent log
    try:
        parsed_url = make_url(url) if url else None
        url_debug = {
            "present": bool(url),
            "drivername": parsed_url.drivername if parsed_url else None,
            "host": parsed_url.host if parsed_url else None,
            "port": parsed_url.port if parsed_url else None,
            "database": parsed_url.database if parsed_url else None,
            "has_password": bool(parsed_url.password) if parsed_url else False,
        }
    except Exception as parse_err:
        url_debug = {"present": bool(url), "parse_error": f"{type(parse_err).__name__}: {parse_err}"}
    _agent_log(
        "pre-fix",
        "H1,H2,H3,H4",
        "ce-db/src/ce_db/engine.py:get_engine.before_create",
        "ce-db engine requested",
        {"url": url_debug, "engine_cached": _engine is not None},
    )
    # endregion
    if not url:
        return None
    if _engine is None:
        try:
            _engine = create_async_engine(url, echo=False, pool_size=5)
        except Exception as e:
            logger.warning("Failed to create DB engine: %s", e)
            # region agent log
            _agent_log(
                "pre-fix",
                "H1,H2",
                "ce-db/src/ce_db/engine.py:get_engine.create_failed",
                "ce-db engine creation failed",
                {"error_type": type(e).__name__, "error": str(e)},
            )
            # endregion
            return None
    return _engine
