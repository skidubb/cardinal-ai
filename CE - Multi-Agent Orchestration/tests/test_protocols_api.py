"""Tests for GET /api/protocols endpoint — integration test via FastAPI TestClient."""

from fastapi.testclient import TestClient

from api.server import app

client = TestClient(app)


def test_protocols_endpoint_returns_list():
    resp = client.get("/api/protocols")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 48


def test_protocols_include_tools_enabled():
    resp = client.get("/api/protocols")
    data = resp.json()
    for p in data:
        assert "tools_enabled" in p, f"Protocol {p['key']} missing tools_enabled"


def test_protocols_include_problem_types():
    resp = client.get("/api/protocols")
    data = resp.json()
    for p in data:
        assert "problem_types" in p
        assert isinstance(p["problem_types"], list)


def test_meta_protocols_tools_disabled_via_api():
    resp = client.get("/api/protocols")
    data = resp.json()
    meta = [p for p in data if p["key"].startswith("p0") and not p["key"][2:3].isdigit()]
    assert len(meta) == 3
    for p in meta:
        assert p["tools_enabled"] is False


def test_health_endpoint():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
