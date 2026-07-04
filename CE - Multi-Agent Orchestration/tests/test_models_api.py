"""Tests for GET /api/models — the model catalog endpoint."""

from __future__ import annotations


def test_list_models_returns_catalog_and_defaults(client):
    resp = client.get("/api/models")
    assert resp.status_code == 200

    body = resp.json()
    assert len(body["models"]) >= 10
    assert set(body["defaults"].keys()) == {"thinking", "orchestration", "balanced"}
    assert body["tiers"] == ["L1", "L2", "L3", "L4"]

    sample = body["models"][0]
    assert {"id", "display_name", "provider", "route", "tier"} <= sample.keys()
