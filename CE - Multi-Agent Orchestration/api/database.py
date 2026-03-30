"""Database setup using SQLModel (Postgres via DATABASE_URL, SQLite fallback)."""

import logging
import os
import sys
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

logger = logging.getLogger(__name__)

_DB_URL_ENV = os.getenv("DATABASE_URL", "")

# --- Diagnostic: always print to stderr so Railway deploy logs capture it ---
def _log(msg: str) -> None:
    print(f"[database.py] {msg}", file=sys.stderr, flush=True)

_log(f"DATABASE_URL present: {bool(_DB_URL_ENV)}, length: {len(_DB_URL_ENV)}")
if _DB_URL_ENV:
    # Show scheme + host (mask credentials)
    _parts = _DB_URL_ENV.split("@")
    _host_part = _parts[-1] if len(_parts) > 1 else "(no @ found)"
    _scheme = _DB_URL_ENV.split("://")[0] if "://" in _DB_URL_ENV else "(no scheme)"
    _log(f"  scheme={_scheme}  host={_host_part}")

# --- SQLite fallback path ---
_DB_PATH = Path(__file__).resolve().parent.parent / "orchestrator.db"
_SQLITE_URL = f"sqlite:///{_DB_PATH}"


def _build_postgres_url(raw: str) -> str:
    """Normalize a Postgres DATABASE_URL for sync psycopg2."""
    url = raw.replace("postgres://", "postgresql://", 1)
    if "+asyncpg" in url:
        url = url.replace("+asyncpg", "+psycopg2")
    elif "postgresql://" in url and "+" not in url.split("://")[0]:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def _create_engine_safe():
    """Create DB engine: try Postgres if DATABASE_URL set, fall back to SQLite."""
    if not _DB_URL_ENV:
        _log("No DATABASE_URL — using SQLite")
        return create_engine(_SQLITE_URL, echo=False, connect_args={"check_same_thread": False}), _SQLITE_URL

    pg_url = _build_postgres_url(_DB_URL_ENV)
    _log(f"Trying Postgres: {pg_url.split('@')[0]}@***")

    try:
        eng = create_engine(pg_url, echo=False, pool_pre_ping=True)
        # Verify the connection actually works before committing to it
        with eng.connect() as conn:
            conn.execute(SQLModel.text("SELECT 1"))
        _log("Postgres connection verified")
        return eng, pg_url
    except Exception as e:
        _log(f"Postgres connection FAILED: {e}")
        _log("Falling back to SQLite")
        return create_engine(_SQLITE_URL, echo=False, connect_args={"check_same_thread": False}), _SQLITE_URL


engine, DATABASE_URL = _create_engine_safe()


def create_db_and_tables() -> None:
    import api.models  # noqa: F401 — ensure models register with SQLModel metadata
    try:
        SQLModel.metadata.create_all(engine)
        _log("create_db_and_tables() succeeded")
    except Exception as e:
        _log(f"create_db_and_tables() failed: {e} — app will start anyway")


def get_session():
    with Session(engine) as session:
        yield session
