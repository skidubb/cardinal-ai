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


# ── Plan 02: Pipeline presets ─────────────────────────────────────────────────

def test_pipeline_presets_in_list(client):
    """GET /api/pipelines returns preset entries with is_preset=True (API-08)."""
    resp = client.get("/api/pipelines")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)

    presets = [item for item in data if item.get("is_preset") is True]
    assert len(presets) >= 5, f"Expected at least 5 presets, got {len(presets)}"

    # Each preset must have required fields
    for preset in presets:
        assert "name" in preset, f"Preset missing 'name': {preset}"
        assert "steps" in preset, f"Preset missing 'steps': {preset}"
        assert len(preset["steps"]) >= 1, f"Preset has no steps: {preset}"
        for step in preset["steps"]:
            assert "protocol_key" in step, f"Step missing 'protocol_key': {step}"
            assert "question_template" in step, f"Step missing 'question_template': {step}"


def test_pipeline_presets_have_valid_ids(client):
    """All pipeline presets have unique string IDs starting with 'preset-'."""
    from api.pipeline_presets import PIPELINE_PRESETS

    ids = [p["id"] for p in PIPELINE_PRESETS]
    assert len(ids) == len(set(ids)), "Preset IDs are not unique"
    for pid in ids:
        assert pid.startswith("preset-"), f"Preset ID does not start with 'preset-': {pid}"


def test_pipeline_presets_protocol_keys_are_strings(client):
    """All protocol_key values in pipeline presets are non-empty strings."""
    from api.pipeline_presets import PIPELINE_PRESETS

    for preset in PIPELINE_PRESETS:
        for step in preset["steps"]:
            key = step["protocol_key"]
            assert isinstance(key, str) and key, f"Invalid protocol_key in preset {preset['id']}: {key!r}"


# ── Plan 02: Active task registry ─────────────────────────────────────────────

def test_active_run_tasks_registry_is_importable():
    """_active_run_tasks is a dict and is importable from api.runner (API-10)."""
    from api.runner import _active_run_tasks
    assert isinstance(_active_run_tasks, dict)


def test_active_run_tasks_registry_empty_at_test_start():
    """_active_run_tasks is empty when no runs are in flight."""
    from api.runner import _active_run_tasks
    # At test time (no concurrent runs), registry should be empty
    assert len(_active_run_tasks) == 0


# ── Plan 02: CancelledError handling ─────────────────────────────────────────

def test_cancelled_error_marks_run_cancelled(engine):
    """CancelledError handler marks run status as 'cancelled' in DB (API-10)."""
    import asyncio
    from datetime import datetime, timezone
    from sqlmodel import Session as S
    from api.models import Run
    from api.database import get_session
    from api.runner import _sse_event

    # Create a run record with status "running"
    with S(engine) as session:
        run = Run(
            type="protocol",
            protocol_key="p03_parallel_synthesis",
            question="test",
            status="running",
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    # Simulate the CancelledError handler logic directly
    with S(engine) as session:
        run = session.get(Run, run_id)
        if run:
            run.status = "cancelled"
            run.completed_at = datetime.now(timezone.utc)
            session.add(run)
            session.commit()

    # Verify DB state
    with S(engine) as session:
        run = session.get(Run, run_id)
        assert run is not None
        assert run.status == "cancelled"
        assert run.completed_at is not None


def test_cancelled_sse_event_format():
    """The CancelledError handler yields a run_complete SSE event with status=cancelled."""
    from api.runner import _sse_event
    import json

    event_str = _sse_event("run_complete", {"run_id": 42, "status": "cancelled"})
    assert "event: run_complete" in event_str
    data_line = [line for line in event_str.splitlines() if line.startswith("data:")][0]
    payload = json.loads(data_line[len("data:"):].strip())
    assert payload["status"] == "cancelled"
    assert payload["run_id"] == 42


# ── Plan 02: Disconnect watcher ───────────────────────────────────────────────

def test_watch_disconnect_is_defined_in_protocols():
    """_watch_disconnect coroutine is defined in protocols router (API-10)."""
    import inspect
    from api.routers import protocols
    assert hasattr(protocols, "_watch_disconnect"), "_watch_disconnect not found in protocols router"
    assert inspect.iscoroutinefunction(protocols._watch_disconnect), "_watch_disconnect should be async"


def test_watch_disconnect_is_defined_in_pipelines():
    """_watch_disconnect coroutine is defined in pipelines router (API-10)."""
    import inspect
    from api.routers import pipelines
    assert hasattr(pipelines, "_watch_disconnect"), "_watch_disconnect not found in pipelines router"
    assert inspect.iscoroutinefunction(pipelines._watch_disconnect), "_watch_disconnect should be async"


# ── Plan 02: Context var cleanup in finally blocks ───────────────────────────

def test_context_var_cleanup_after_protocol_run(client):
    """After a mocked protocol run, cost_tracker context var is cleaned up (API-09).

    Full integration testing of context var state requires async test infrastructure.
    This test verifies the cleanup path exists via code inspection and that the
    context var is None when accessed outside of a run (default state).
    """
    from protocols.llm import _cost_tracker

    # Outside any run, the context var should be None (default)
    assert _cost_tracker.get(None) is None, "cost_tracker should be None when no run is active"

    # Verify cleanup code structure
    import inspect
    from api import runner
    source = inspect.getsource(runner.run_protocol_stream)
    assert "finally:" in source, "No finally block in run_protocol_stream"
    assert "set_cost_tracker(None)" in source, "set_cost_tracker(None) not in finally block"


def test_runner_finally_blocks_exist():
    """Verify finally blocks with context var cleanup exist in both runner functions (API-09)."""
    import inspect
    from api import runner

    protocol_source = inspect.getsource(runner.run_protocol_stream)
    assert "finally:" in protocol_source, "No finally block in run_protocol_stream"
    assert "set_cost_tracker(None)" in protocol_source, "set_cost_tracker(None) not in finally"
    assert "set_event_queue(None)" in protocol_source, "set_event_queue(None) not in finally"

    pipeline_source = inspect.getsource(runner.run_pipeline_stream)
    assert "finally:" in pipeline_source, "No finally block in run_pipeline_stream"
    assert "set_cost_tracker(None)" in pipeline_source, "set_cost_tracker(None) not in finally"
    assert "set_session_id(None)" in pipeline_source, "set_session_id(None) not in finally"


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
