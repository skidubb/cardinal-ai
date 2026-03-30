"""Database setup using SQLModel (Postgres via DATABASE_URL, SQLite fallback)."""

import os
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

_DB_URL_ENV = os.getenv("DATABASE_URL", "")

if _DB_URL_ENV:
    # Railway Postgres provides DATABASE_URL. SQLAlchemy needs postgresql:// not postgres://.
    DATABASE_URL = _DB_URL_ENV.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL, echo=False)
else:
    # Local dev fallback: SQLite
    _DB_PATH = Path(__file__).resolve().parent.parent / "orchestrator.db"
    DATABASE_URL = f"sqlite:///{_DB_PATH}"
    engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


def create_db_and_tables() -> None:
    import api.models  # noqa: F401 — ensure models register with SQLModel metadata
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
