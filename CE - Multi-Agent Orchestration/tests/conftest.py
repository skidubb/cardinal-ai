"""Shared test fixtures for API endpoint tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool


# ── In-memory SQLite engine ───────────────────────────────────────────────────

@pytest.fixture(name="engine")
def engine_fixture():
    """Create an in-memory SQLite engine for tests."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    import api.models  # noqa: F401 — registers models with SQLModel metadata
    SQLModel.metadata.create_all(test_engine)
    yield test_engine
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture(name="session")
def session_fixture(engine):
    """Create a test DB session."""
    with Session(engine) as session:
        yield session


# ── TestClient fixture ────────────────────────────────────────────────────────

@pytest.fixture(name="client")
def client_fixture(engine):
    """Create a TestClient with in-memory DB and no-op lifespan."""

    # Override get_session to use the test engine
    def override_get_session():
        with Session(engine) as session:
            yield session

    # No-op lifespan — skips SdkAgent import check
    @asynccontextmanager
    async def noop_lifespan(app):
        # Create tables in the test engine instead of the production engine
        import api.models  # noqa: F401
        SQLModel.metadata.create_all(engine)
        yield

    with (
        patch("api.server.lifespan", noop_lifespan),
        patch("api.database.engine", engine),
        patch("api.routers.runs.engine", engine),
        patch("api.routers.protocols.engine", engine, create=True),
        patch("api.routers.pipelines.engine", engine, create=True),
        patch("api.runner.engine", engine),
    ):
        from api.server import app
        from api.database import get_session

        app.dependency_overrides[get_session] = override_get_session

        with TestClient(app, raise_server_exceptions=False) as c:
            yield c

        app.dependency_overrides.clear()


# ── SSE async generator helpers ───────────────────────────────────────────────

async def _mock_protocol_stream(*args, **kwargs) -> AsyncGenerator[str, None]:
    """Mock run_protocol_stream that yields minimal SSE events."""
    yield 'event: run_start\ndata: {"run_id": 1}\n\n'
    yield 'event: run_complete\ndata: {"run_id": 1, "status": "completed"}\n\n'


async def _mock_pipeline_stream(*args, **kwargs) -> AsyncGenerator[str, None]:
    """Mock run_pipeline_stream that yields minimal SSE events."""
    yield 'event: run_start\ndata: {"run_id": 1, "type": "pipeline"}\n\n'
    yield 'event: run_complete\ndata: {"run_id": 1, "status": "completed"}\n\n'
