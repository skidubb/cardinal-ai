"""Verify the Clerk webhook handler.

Tests:
  1. Missing svix headers -> 400
  2. Bad signature -> 401
  3. Valid signature, organization.created -> 200 with provisioning slug
  4. Valid signature, unknown event -> 200 ack
  5. _slugify produces valid slugs

Uses a fake Clerk webhook secret + Svix to sign test payloads.
"""

from __future__ import annotations

import json
import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from svix.webhooks import Webhook

# Set a known secret BEFORE importing the handler so module load picks it up.
os.environ["CLERK_WEBHOOK_SECRET"] = (
    "whsec_MfKQ9r8GKYqrTwjUPD8ILPZIo2LaLaSw"  # base64 dummy, valid Svix format
)


def _make_app():
    from api.routers.webhooks_clerk import router
    app = FastAPI()
    app.include_router(router)
    return app


def _signed_headers(body: bytes, msg_id: str = "msg_test_1") -> dict:
    from datetime import datetime, timezone
    wh = Webhook(os.environ["CLERK_WEBHOOK_SECRET"])
    now = datetime.now(timezone.utc)
    timestamp_str = str(int(now.timestamp()))
    sig = wh.sign(msg_id, now, body.decode())
    return {
        "svix-id": msg_id,
        "svix-timestamp": timestamp_str,
        "svix-signature": sig,
        "content-type": "application/json",
    }


def test_missing_headers_returns_400() -> None:
    client = TestClient(_make_app())
    r = client.post("/api/webhooks/clerk", content=b"{}", headers={"content-type": "application/json"})
    assert r.status_code == 400


def test_bad_signature_returns_401() -> None:
    client = TestClient(_make_app())
    r = client.post(
        "/api/webhooks/clerk",
        content=b"{}",
        headers={
            "svix-id": "msg_x",
            "svix-timestamp": "1700000000",
            "svix-signature": "v1,wrong",
            "content-type": "application/json",
        },
    )
    assert r.status_code == 401


def test_organization_created_provisions_slug(monkeypatch) -> None:
    """Valid signed organization.created payload -> 200, returns provisioning slug."""
    # Stub out the actual provisioning subprocess so the test doesn't try to run cegraph
    import api.routers.webhooks_clerk as wh_mod

    async def _noop(slug: str) -> None:
        pass

    monkeypatch.setattr(wh_mod, "_provision_tenant_graph", _noop)

    payload = json.dumps({
        "type": "organization.created",
        "data": {"id": "org_test_123", "slug": "imagine-wireless", "name": "Imagine Wireless"},
    }).encode()
    headers = _signed_headers(payload)
    client = TestClient(_make_app())
    r = client.post("/api/webhooks/clerk", content=payload, headers=headers)
    assert r.status_code == 200
    assert r.json() == {"ok": True, "provisioning": "imagine-wireless"}


def test_unknown_event_returns_ok() -> None:
    payload = json.dumps({"type": "user.created", "data": {"id": "user_x"}}).encode()
    headers = _signed_headers(payload)
    client = TestClient(_make_app())
    r = client.post("/api/webhooks/clerk", content=payload, headers=headers)
    assert r.status_code == 200
    assert r.json() == {"ok": True, "event": "user.created"}


def test_organization_deleted_does_not_drop_graph() -> None:
    """Deletion is logged but graph is preserved (manual cleanup required)."""
    payload = json.dumps({
        "type": "organization.deleted",
        "data": {"id": "org_x", "slug": "acme"},
    }).encode()
    headers = _signed_headers(payload)
    client = TestClient(_make_app())
    r = client.post("/api/webhooks/clerk", content=payload, headers=headers)
    assert r.status_code == 200
    assert r.json() == {"ok": True, "manual_cleanup_required": "acme"}


def test_slugify_normalizes_names() -> None:
    from api.routers.webhooks_clerk import _slugify
    assert _slugify("Acme Corp") == "acme-corp"
    assert _slugify("ACME!  Corp.") == "acme-corp"
    assert _slugify("  ") == "tenant"
    assert _slugify("Imagine Wireless 2026") == "imagine-wireless-2026"


def test_health_endpoint() -> None:
    client = TestClient(_make_app())
    r = client.get("/api/webhooks/clerk/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "secret_configured": True}
