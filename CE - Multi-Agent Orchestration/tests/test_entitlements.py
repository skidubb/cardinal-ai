"""Tests for the subscription entitlements layer (api/entitlements.py).

Covers claim parsing (v2 session token vs legacy ce-railway template),
plan -> limits mapping, the monthly quota window/query, admission + feature
enforcement (including the ENTITLEMENTS_ENFORCE dry-run kill switch), and
the endpoint-level 402 contract on POST /api/protocols/run.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from api.entitlements import (
    FEATURE_KNOWLEDGE_GRAPH,
    FEATURE_PREMIUM_PROTOCOLS,
    FREE_PROTOCOL_KEYS,
    TenantEntitlements,
    check_protocol_allowed,
    entitlements_from_auth,
    get_entitlements,
    month_window,
    plan_defaults,
    require_feature,
    require_run_admission,
    runs_used_this_month,
)
from api.middleware.clerk_auth import _parse_claims
from api.models import Run


@pytest.fixture(autouse=True)
def _enforce_on(monkeypatch: pytest.MonkeyPatch):
    """Default tests to enforcement ON; dry-run tests override explicitly."""
    monkeypatch.setenv("ENTITLEMENTS_ENFORCE", "1")


def _te(plan: str = "free", tenant: str = "acme") -> TenantEntitlements:
    return TenantEntitlements(tenant, plan_defaults(plan), None)


# ── _parse_claims: v2 session token vs legacy template ────────────────────────


def test_parse_claims_v2_session_token():
    claims = {
        "v": 2,
        "sub": "user_123",
        "o": {"id": "org_abc", "slg": "acme", "rol": "admin"},
        "pla": "o:pro",
        "fea": "o:premium_protocols,o:knowledge_graph",
    }
    ctx = _parse_claims(claims)
    assert ctx.user_id == "user_123"
    assert ctx.org_id == "org_abc"
    assert ctx.org_slug == "acme"
    assert ctx.org_role == "org:admin"
    assert ctx.plan == "pro"
    assert ctx.features == frozenset({"premium_protocols", "knowledge_graph"})


def test_parse_claims_v2_user_payer_ignored():
    """User-payer plans/features (u:) don't grant org entitlements."""
    claims = {"v": 2, "sub": "u1", "o": {"slg": "acme"}, "pla": "u:pro", "fea": "u:x"}
    ctx = _parse_claims(claims)
    assert ctx.plan is None
    assert ctx.features == frozenset()


def test_parse_claims_v2_uo_payer_counts():
    """Clerk encodes 'either payer' as 'uo:' -- org side should count."""
    claims = {"v": 2, "sub": "u1", "o": {"slg": "acme"}, "fea": "uo:knowledge_graph"}
    ctx = _parse_claims(claims)
    assert "knowledge_graph" in ctx.features


def test_parse_claims_legacy_template():
    claims = {
        "sub": "user_123",
        "org_id": "org_abc",
        "org_slug": "acme",
        "org_role": "org:member",
        "tier": "2",
    }
    ctx = _parse_claims(claims)
    assert ctx.org_slug == "acme"
    assert ctx.org_role == "org:member"
    assert ctx.tier == 2
    assert ctx.plan is None
    assert ctx.features == frozenset()


def test_parse_claims_garbage_is_free():
    ctx = _parse_claims({"sub": "u1", "pla": "nonsense", "fea": 42, "tier": "abc"})
    assert ctx.plan is None
    assert ctx.features == frozenset()
    assert ctx.tier is None


# ── plan mapping ──────────────────────────────────────────────────────────────


def test_entitlements_from_auth_v2_pro():
    ctx = _parse_claims(
        {
            "v": 2,
            "sub": "u",
            "o": {"slg": "acme"},
            "pla": "o:pro",
            "fea": "o:premium_protocols",
        }
    )
    ent = entitlements_from_auth(ctx)
    assert ent.plan == "pro"
    assert ent.runs_per_month == 100
    # fea claim is authoritative when present
    assert ent.features == frozenset({"premium_protocols"})


def test_entitlements_from_auth_unknown_plan_is_free():
    ctx = _parse_claims({"v": 2, "sub": "u", "o": {"slg": "acme"}, "pla": "o:free_org"})
    ent = entitlements_from_auth(ctx)
    assert ent.plan == "free"
    assert ent.features == frozenset()


def test_entitlements_from_auth_legacy_tier_fallback():
    ctx = _parse_claims({"sub": "u", "org_slug": "acme", "tier": 3})
    ent = entitlements_from_auth(ctx)
    assert ent.plan == "enterprise"
    assert ent.runs_per_month is None


def test_entitlements_from_auth_none_is_internal():
    ent = entitlements_from_auth(None)
    assert ent.plan == "internal"
    assert ent.runs_per_month is None
    assert ent.run_cost_ceiling_usd is None
    assert FEATURE_PREMIUM_PROTOCOLS in ent.features


def test_plan_defaults_env_overrides(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CE_FREE_RUNS_PER_MONTH", "2")
    monkeypatch.setenv("CE_FREE_RUN_COST_CAP", "0.01")
    ent = plan_defaults("free")
    assert ent.runs_per_month == 2
    assert ent.run_cost_ceiling_usd == 0.01


# ── month window + usage query ────────────────────────────────────────────────


def test_month_window_mid_year():
    start, end = month_window(datetime(2026, 7, 4, 12, 30, tzinfo=timezone.utc))
    assert start == datetime(2026, 7, 1, tzinfo=timezone.utc)
    assert end == datetime(2026, 8, 1, tzinfo=timezone.utc)


def test_month_window_december_rollover():
    start, end = month_window(datetime(2026, 12, 31, 23, 59, tzinfo=timezone.utc))
    assert start == datetime(2026, 12, 1, tzinfo=timezone.utc)
    assert end == datetime(2027, 1, 1, tzinfo=timezone.utc)


def _add_run(
    session: Session,
    tenant: str,
    status: str = "completed",
    started_at: datetime | None = None,
) -> None:
    session.add(
        Run(
            type="protocol",
            protocol_key="p00_direct",
            question="q",
            status=status,
            tenant_slug=tenant,
            started_at=started_at or datetime.now(timezone.utc),
        )
    )
    session.commit()


def test_runs_used_this_month_filters(session: Session):
    now = datetime.now(timezone.utc)
    _add_run(session, "acme")  # counts
    _add_run(session, "acme", status="running")  # counts
    _add_run(session, "acme", status="failed")  # excluded
    _add_run(session, "acme", started_at=now - timedelta(days=45))  # last month
    _add_run(session, "other-tenant")  # other tenant
    assert runs_used_this_month(session, "acme") == 2


# ── admission + feature enforcement ───────────────────────────────────────────


def test_require_run_admission_402_when_over_limit(session: Session):
    for _ in range(5):
        _add_run(session, "acme")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(require_run_admission(_te("free"), session))
    exc = exc_info.value
    assert exc.status_code == 402
    assert exc.detail["code"] == "quota_exceeded"
    assert exc.detail["used"] == 5
    assert exc.detail["limit"] == 5
    assert exc.detail["upgrade_url"] == "/billing"


def test_require_run_admission_allows_under_limit(session: Session):
    _add_run(session, "acme")
    te = asyncio.run(require_run_admission(_te("free"), session))
    assert te.tenant_slug == "acme"


def test_require_run_admission_unlimited_plans_skip_query(session: Session):
    for _ in range(10):
        _add_run(session, "acme")
    te = asyncio.run(require_run_admission(_te("internal"), session))
    assert te.entitlements.plan == "internal"


def test_require_run_admission_dry_run_does_not_block(
    session: Session, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("ENTITLEMENTS_ENFORCE", "0")
    for _ in range(5):
        _add_run(session, "acme")
    te = asyncio.run(require_run_admission(_te("free"), session))
    assert te.entitlements.plan == "free"  # passed through, only logged


def test_require_feature_403():
    dep = require_feature(FEATURE_KNOWLEDGE_GRAPH)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(dep(_te("free")))
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "feature_required"
    assert exc_info.value.detail["feature"] == FEATURE_KNOWLEDGE_GRAPH


def test_require_feature_passes_for_pro():
    dep = require_feature(FEATURE_KNOWLEDGE_GRAPH)
    te = asyncio.run(dep(_te("pro")))
    assert te.entitlements.plan == "pro"


def test_check_protocol_allowed_free_key():
    check_protocol_allowed("p00_direct", _te("free"))  # no raise
    assert "p00_direct" in FREE_PROTOCOL_KEYS


def test_check_protocol_allowed_premium_blocked_on_free():
    with pytest.raises(HTTPException) as exc_info:
        check_protocol_allowed("p04_multi_round_debate", _te("free"))
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["protocol_key"] == "p04_multi_round_debate"


def test_check_protocol_allowed_premium_ok_on_pro():
    check_protocol_allowed("p04_multi_round_debate", _te("pro"))  # no raise


# ── endpoint-level contract: 402 before any Run row is created ────────────────


def test_protocol_run_402_at_limit_creates_no_run(client, engine, monkeypatch):
    monkeypatch.setenv("ENTITLEMENTS_ENFORCE", "1")
    from api.server import app

    with Session(engine) as session:
        for _ in range(5):
            _add_run(session, "acme")

    async def override_entitlements():
        return _te("free")

    app.dependency_overrides[get_entitlements] = override_entitlements
    try:
        resp = client.post(
            "/api/protocols/run",
            json={
                "protocol_key": "p00_direct",
                "question": "over the limit?",
                "agent_keys": [],
            },
        )
    finally:
        app.dependency_overrides.pop(get_entitlements, None)

    assert resp.status_code == 402
    body = resp.json()
    assert body["detail"]["code"] == "quota_exceeded"

    with Session(engine) as session:
        from sqlmodel import func, select

        count = session.exec(select(func.count()).select_from(Run)).one()
    assert int(count) == 5  # nothing new was created


def test_protocol_run_premium_403_for_free_org(client, monkeypatch):
    monkeypatch.setenv("ENTITLEMENTS_ENFORCE", "1")
    from api.server import app

    async def override_entitlements():
        return _te("free")

    app.dependency_overrides[get_entitlements] = override_entitlements
    try:
        resp = client.post(
            "/api/protocols/run",
            json={
                "protocol_key": "p04_multi_round_debate",
                "question": "premium?",
                "agent_keys": ["ceo"],
            },
        )
    finally:
        app.dependency_overrides.pop(get_entitlements, None)

    assert resp.status_code == 403
    assert resp.json()["detail"]["feature"] == FEATURE_PREMIUM_PROTOCOLS


def test_protocol_run_allowed_for_pro_org(client, monkeypatch):
    monkeypatch.setenv("ENTITLEMENTS_ENFORCE", "1")
    from api.server import app
    from tests.conftest import _mock_protocol_stream

    async def override_entitlements():
        return _te("pro")

    app.dependency_overrides[get_entitlements] = override_entitlements
    try:
        with patch(
            "api.routers.protocols.run_protocol_stream",
            side_effect=_mock_protocol_stream,
        ):
            resp = client.post(
                "/api/protocols/run",
                json={
                    "protocol_key": "p04_multi_round_debate",
                    "question": "pro can run premium",
                    "agent_keys": ["ceo"],
                },
            )
    finally:
        app.dependency_overrides.pop(get_entitlements, None)

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")


# ── usage endpoint contract ───────────────────────────────────────────────────


def test_usage_includes_period_and_plan_fields(client, engine, monkeypatch):
    from api.server import app

    with Session(engine) as session:
        _add_run(session, "acme")
        _add_run(session, "acme", status="failed")

    async def override_entitlements():
        return _te("free")

    app.dependency_overrides[get_entitlements] = override_entitlements
    try:
        resp = client.get("/api/usage")
    finally:
        app.dependency_overrides.pop(get_entitlements, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] == "free"
    assert body["period_runs"] == 1  # failed run excluded
    assert body["runs_limit"] == 5
    assert body["runs_remaining"] == 4
    assert body["run_cost_cap_usd"] == 0.5
    assert body["total_runs"] == 2  # all-time still counts everything
