"""M3 endpoint tests: /api/usage + /api/connectors.

Uses in-memory SQLite + FastAPI TestClient. No Postgres, no Railway infra.
"""

from __future__ import annotations

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture
def test_app(monkeypatch):
    """Build a fresh app + in-memory DB. Monkey-patches api.database.engine
    so the real get_session picks up our test engine."""
    from api import database as db_module
    from api.models import Run

    # StaticPool shares a single connection across threads -- required for
    # SQLite in-memory DBs where each connection otherwise gets its own fresh DB.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as s:
        s.add(Run(type="protocol", protocol_key="p04", question="a1", tenant_slug="acme", status="completed", cost_usd=0.05))
        s.add(Run(type="protocol", protocol_key="p06", question="a2", tenant_slug="acme", status="completed", cost_usd=0.10))
        s.add(Run(type="protocol", protocol_key="p06", question="a3", tenant_slug="acme", status="failed", cost_usd=0.01))
        s.add(Run(type="protocol", protocol_key="p04", question="w1", tenant_slug="workload", status="completed", cost_usd=0.50))
        s.add(Run(type="protocol", protocol_key="p04", question="c1", tenant_slug="cardinal-element", status="completed", cost_usd=0.25))
        s.commit()

    monkeypatch.setattr(db_module, "engine", engine)

    from api.routers import usage, connectors as conn_router

    app = FastAPI()
    app.include_router(usage.router)
    app.include_router(conn_router.router)
    return app


def test_usage_aggregates_per_tenant(test_app, monkeypatch) -> None:
    monkeypatch.setenv("CE_DEV_TENANT", "acme")
    monkeypatch.delenv("CLERK_JWKS_URL", raising=False)
    from api.middleware.clerk_auth import _config
    _config.cache_clear()

    client = TestClient(test_app)
    r = client.get("/api/usage")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["tenant_slug"] == "acme"
    assert data["total_runs"] == 3
    assert abs(data["total_cost_usd"] - 0.16) < 1e-6
    assert data["completed_runs"] == 2
    assert abs(data["completed_cost_usd"] - 0.15) < 1e-6
    assert "failed" in data["by_status"]


def test_usage_isolated_across_tenants(test_app, monkeypatch) -> None:
    monkeypatch.delenv("CLERK_JWKS_URL", raising=False)
    from api.middleware.clerk_auth import _config

    monkeypatch.setenv("CE_DEV_TENANT", "workload")
    _config.cache_clear()
    r = TestClient(test_app).get("/api/usage")
    assert r.status_code == 200
    wl = r.json()
    assert wl["total_runs"] == 1
    assert abs(wl["total_cost_usd"] - 0.50) < 1e-6

    monkeypatch.setenv("CE_DEV_TENANT", "cardinal-element")
    _config.cache_clear()
    r = TestClient(test_app).get("/api/usage")
    assert r.status_code == 200
    ce = r.json()
    assert ce["total_runs"] == 1
    assert abs(ce["total_cost_usd"] - 0.25) < 1e-6

    # Cross-tenant sanity: acme's runs never leak into workload's usage
    assert wl["total_cost_usd"] != ce["total_cost_usd"]


def test_connectors_status_returns_all_known(test_app, monkeypatch) -> None:
    monkeypatch.delenv("CLERK_JWKS_URL", raising=False)
    monkeypatch.setenv("CE_DEV_TENANT", "cardinal-element")
    from api.middleware.clerk_auth import _config
    _config.cache_clear()

    client = TestClient(test_app)
    r = client.get("/api/connectors/status")
    assert r.status_code == 200
    data = r.json()
    assert data["tenant_slug"] == "cardinal-element"
    names = {c["name"] for c in data["connectors"]}
    assert {"hubspot", "notion", "granola", "google_drive", "slack", "gmail"}.issubset(names)

    # HubSpot should be flagged direct_api; Notion mcp_driven
    by_name = {c["name"]: c for c in data["connectors"]}
    assert by_name["hubspot"]["mode"] == "direct_api"
    assert by_name["notion"]["mode"] == "mcp_driven"


def test_connector_start_mcp_returns_runbook(test_app, monkeypatch) -> None:
    monkeypatch.delenv("CLERK_JWKS_URL", raising=False)
    monkeypatch.setenv("CE_DEV_TENANT", "imagine-wireless")
    from api.middleware.clerk_auth import _config
    _config.cache_clear()

    client = TestClient(test_app)
    r = client.post("/api/connectors/start", json={"connector": "notion", "since": "2026-01-01"})
    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "mcp_runbook"
    assert data["tenant_slug"] == "imagine-wireless"
    assert data["status"] == "runbook_only"
    assert "imagine-wireless" in data["runbook"]
    assert "2026-01-01" in data["runbook"]


def test_connector_start_direct_api_queues(test_app, monkeypatch) -> None:
    monkeypatch.delenv("CLERK_JWKS_URL", raising=False)
    monkeypatch.setenv("CE_DEV_TENANT", "cardinal-element")
    from api.middleware.clerk_auth import _config
    _config.cache_clear()

    # Stub the subprocess so we don't actually spawn anything
    import api.routers.connectors as conn_mod

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(conn_mod, "_run_cegraph_backfill", _noop)

    client = TestClient(test_app)
    r = client.post("/api/connectors/start", json={"connector": "hubspot", "dry_run": True})
    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "direct_api"
    assert data["status"] == "queued"
    assert data["runbook"] is None


def test_connector_start_unknown_returns_400(test_app, monkeypatch) -> None:
    monkeypatch.delenv("CLERK_JWKS_URL", raising=False)
    monkeypatch.setenv("CE_DEV_TENANT", "cardinal-element")
    from api.middleware.clerk_auth import _config
    _config.cache_clear()

    client = TestClient(test_app)
    r = client.post("/api/connectors/start", json={"connector": "myspace"})
    assert r.status_code == 400
