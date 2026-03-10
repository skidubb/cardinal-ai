"""TestClient-based tests for the API endpoints.

Verifies URL structure, SSE headers, and basic CRUD for all canonical routes.
Run via: pytest tests/test_api_endpoints.py -x -q
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _fake_protocol_stream(*args, **kwargs) -> AsyncGenerator[str, None]:
    yield 'event: run_start\ndata: {"run_id": 1}\n\n'
    yield 'event: run_complete\ndata: {"run_id": 1, "status": "completed"}\n\n'


async def _fake_pipeline_stream(*args, **kwargs) -> AsyncGenerator[str, None]:
    yield 'event: run_start\ndata: {"run_id": 1, "type": "pipeline"}\n\n'
    yield 'event: run_complete\ndata: {"run_id": 1, "status": "completed"}\n\n'


# ── Basic health / list endpoints ─────────────────────────────────────────────

def test_health_returns_200(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_protocols_returns_list(client):
    """GET /api/protocols returns a list (API-03 — read-only manifest)."""
    resp = client.get("/api/protocols")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_agents_returns_list(client):
    """GET /api/agents returns a list (API-04)."""
    resp = client.get("/api/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_runs_returns_empty_list(client):
    """GET /api/runs returns empty list with 200 (API-05)."""
    resp = client.get("/api/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_get_nonexistent_run_returns_404(client):
    """GET /api/runs/999 returns 404 (API-06 edge case)."""
    resp = client.get("/api/runs/999")
    assert resp.status_code == 404


# ── POST /api/protocols/run (API-01 + API-02) ─────────────────────────────────

def test_protocol_run_returns_sse_content_type(client):
    """POST /api/protocols/run returns text/event-stream (API-01)."""
    payload = {
        "protocol_key": "p03_parallel_synthesis",
        "question": "Test question",
        "agent_keys": ["ceo", "cfo"],
    }
    with patch("api.routers.protocols.run_protocol_stream", side_effect=_fake_protocol_stream):
        resp = client.post("/api/protocols/run", json=payload)
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")


def test_protocol_run_has_accel_buffering_header(client):
    """POST /api/protocols/run includes X-Accel-Buffering: no (API-02)."""
    payload = {
        "protocol_key": "p03_parallel_synthesis",
        "question": "Test question",
        "agent_keys": ["ceo", "cfo"],
    }
    with patch("api.routers.protocols.run_protocol_stream", side_effect=_fake_protocol_stream):
        resp = client.post("/api/protocols/run", json=payload)
    assert resp.status_code == 200
    assert resp.headers.get("x-accel-buffering") == "no"


def test_protocol_run_creates_run_record(client):
    """POST /api/protocols/run creates a DB run record."""
    payload = {
        "protocol_key": "p03_parallel_synthesis",
        "question": "Test question",
        "agent_keys": ["ceo", "cfo"],
    }
    with patch("api.routers.protocols.run_protocol_stream", side_effect=_fake_protocol_stream):
        client.post("/api/protocols/run", json=payload)
    # After run, the runs list should have one entry
    resp = client.get("/api/runs")
    assert resp.status_code == 200
    runs = resp.json()
    assert len(runs) >= 1


def test_protocol_run_missing_fields_returns_422(client):
    """POST /api/protocols/run with missing fields returns 422."""
    resp = client.post("/api/protocols/run", json={"protocol_key": "p03_parallel_synthesis"})
    assert resp.status_code == 422


# ── POST /api/pipelines/run (API-07 + API-02) ─────────────────────────────────

def test_pipeline_run_returns_sse_content_type(client):
    """POST /api/pipelines/run returns text/event-stream (API-07)."""
    payload = {
        "question": "Pipeline question",
        "agent_keys": ["ceo", "cfo"],
        "steps": [
            {
                "protocol_key": "p03_parallel_synthesis",
                "question_template": "Analyze: {prev_output}",
            }
        ],
    }
    with patch("api.routers.pipelines.run_pipeline_stream", side_effect=_fake_pipeline_stream):
        resp = client.post("/api/pipelines/run", json=payload)
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")


def test_pipeline_run_has_accel_buffering_header(client):
    """POST /api/pipelines/run includes X-Accel-Buffering: no (API-02)."""
    payload = {
        "question": "Pipeline question",
        "agent_keys": ["ceo", "cfo"],
        "steps": [
            {
                "protocol_key": "p03_parallel_synthesis",
                "question_template": "Analyze: {prev_output}",
            }
        ],
    }
    with patch("api.routers.pipelines.run_pipeline_stream", side_effect=_fake_pipeline_stream):
        resp = client.post("/api/pipelines/run", json=payload)
    assert resp.status_code == 200
    assert resp.headers.get("x-accel-buffering") == "no"


# ── Old routes no longer exist ────────────────────────────────────────────────

def test_old_protocol_route_is_gone(client):
    """POST /api/runs/protocol should return 404 or 405 — old run endpoint removed."""
    payload = {
        "protocol_key": "p03_parallel_synthesis",
        "question": "Test question",
        "agent_keys": ["ceo", "cfo"],
    }
    resp = client.post("/api/runs/protocol", json=payload)
    # 404 = not found; 405 = method not allowed (path exists for GET but not POST)
    # Either indicates the old POST /api/runs/protocol endpoint is gone.
    assert resp.status_code in (404, 405)


def test_old_pipeline_route_is_gone(client):
    """POST /api/runs/pipeline should return 404 or 405 — old run endpoint removed."""
    payload = {
        "question": "Pipeline question",
        "agent_keys": ["ceo"],
        "steps": [],
    }
    resp = client.post("/api/runs/pipeline", json=payload)
    assert resp.status_code in (404, 405)


# ── GET /api/runs/{id}/stream (API-02 replay) ─────────────────────────────────

def test_stream_nonexistent_run_returns_404(client):
    """GET /api/runs/999/stream returns 404 for unknown run."""
    resp = client.get("/api/runs/999/stream")
    assert resp.status_code == 404


def test_stream_pending_run_returns_202(client, session):
    """GET /api/runs/{id}/stream returns 202 for a run still in progress."""
    from api.models import Run

    run = Run(type="protocol", protocol_key="p03_parallel_synthesis", question="q", status="pending")
    session.add(run)
    session.commit()
    session.refresh(run)

    # Override session to use the same in-memory DB
    from api.database import get_session

    def override():
        yield session

    from api.server import app
    app.dependency_overrides[get_session] = override

    resp = client.get(f"/api/runs/{run.id}/stream")
    assert resp.status_code == 202

    app.dependency_overrides.pop(get_session, None)


def test_stream_completed_run_returns_sse(client, engine):
    """GET /api/runs/{id}/stream for a completed run returns SSE events."""
    from sqlmodel import Session as S
    from api.models import Run, AgentOutput
    from api.database import get_session

    with S(engine) as session:
        run = Run(
            type="protocol",
            protocol_key="p03_parallel_synthesis",
            question="q",
            status="completed",
            trace_id="test-trace-123",
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

        ao = AgentOutput(
            run_id=run_id,
            agent_key="ceo",
            model="claude-opus-4-6",
            output_text="CEO output here",
        )
        session.add(ao)
        session.commit()

    def override():
        with S(engine) as sess:
            yield sess

    from api.server import app
    app.dependency_overrides[get_session] = override

    resp = client.get(f"/api/runs/{run_id}/stream")
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    body = resp.text
    assert "run_start" in body
    assert "run_complete" in body

    app.dependency_overrides.pop(get_session, None)


# ── GET /api/runs/{id} includes trace_id ──────────────────────────────────────

def test_get_run_includes_trace_id(client, engine):
    """GET /api/runs/{id} response body includes trace_id field (API-06)."""
    from sqlmodel import Session as S
    from api.models import Run
    from api.database import get_session

    with S(engine) as session:
        run = Run(
            type="protocol",
            protocol_key="p03_parallel_synthesis",
            question="q",
            status="completed",
            trace_id="lf-trace-abc123",
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    def override():
        with S(engine) as sess:
            yield sess

    from api.server import app
    app.dependency_overrides[get_session] = override

    resp = client.get(f"/api/runs/{run_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "trace_id" in data
    assert data["trace_id"] == "lf-trace-abc123"

    app.dependency_overrides.pop(get_session, None)
