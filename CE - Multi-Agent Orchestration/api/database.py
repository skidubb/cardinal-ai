"""Database setup using SQLModel (Postgres via DATABASE_URL, SQLite fallback)."""

import logging
import os
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

logger = logging.getLogger(__name__)

_DB_URL_ENV = os.getenv("DATABASE_URL", "")

# Diagnostic: show what DATABASE_URL looks like at import time
if _DB_URL_ENV:
    _masked = _DB_URL_ENV[:25] + "..." if len(_DB_URL_ENV) > 25 else _DB_URL_ENV
    logger.info("DATABASE_URL is set (%d chars): %s", len(_DB_URL_ENV), _masked)
    print(f"[database.py] DATABASE_URL is set ({len(_DB_URL_ENV)} chars): {_masked}")
else:
    logger.info("DATABASE_URL is empty — falling back to SQLite")
    print("[database.py] DATABASE_URL is empty — falling back to SQLite")

if _DB_URL_ENV:
    # Railway Postgres provides DATABASE_URL. SQLAlchemy needs postgresql:// not postgres://.
    DATABASE_URL = _DB_URL_ENV.replace("postgres://", "postgresql://", 1)
    # Force sync psycopg2 driver — asyncpg is installed (from ce-db) but can't be used
    # with synchronous create_engine(). Without this, SQLAlchemy picks asyncpg and crashes.
    if "+asyncpg" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("+asyncpg", "+psycopg2")
    elif "postgresql://" in DATABASE_URL and "+" not in DATABASE_URL.split("://")[0]:
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
    print(f"[database.py] Using Postgres engine: {DATABASE_URL.split('@')[0]}@***")
    engine = create_engine(DATABASE_URL, echo=False)
else:
    # Local dev fallback: SQLite
    _DB_PATH = Path(__file__).resolve().parent.parent / "orchestrator.db"
    DATABASE_URL = f"sqlite:///{_DB_PATH}"
    print(f"[database.py] Using SQLite engine: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


def create_db_and_tables() -> None:
    import api.models  # noqa: F401 — ensure models register with SQLModel metadata
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
