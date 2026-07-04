"""Subscription entitlements: plan -> limits mapping + enforcement dependencies.

The source of truth for a tenant's plan is the Clerk session token (``pla`` /
``fea`` claims, parsed in ``api.middleware.clerk_auth``). This module maps
plan slugs to concrete limits and exposes FastAPI dependencies that enforce
them on money-spending endpoints:

- ``get_entitlements``      -- resolve tenant + entitlements (no enforcement)
- ``require_run_admission`` -- 402 when the monthly run quota is exhausted
- ``require_feature(name)`` -- 403 when the org's plan lacks a feature
- ``check_protocol_allowed`` -- 403 for premium protocols on the free plan

Enforcement is gated behind ``ENTITLEMENTS_ENFORCE`` (default off = log-only
dry run), so the backend can deploy before Clerk Billing is configured and
enforcement flips on via env change alone.

Callers without a Bearer token (X-API-Key internal console, local dev
fallback) get the ``internal`` plan: unlimited, all features. Quota keys use
the canonicalized org slug -- the same value stamped on ``Run.tenant_slug``.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from sqlmodel import Session, func, select

from api.database import get_session
from api.middleware.clerk_auth import (
    ClerkAuthContext,
    _bearer_token,
    _canonicalize_slug,
    get_auth,
    resolve_tenant,
)
from api.models import Run

logger = logging.getLogger(__name__)

FEATURE_PREMIUM_PROTOCOLS = "premium_protocols"
FEATURE_KNOWLEDGE_GRAPH = "knowledge_graph"
FEATURE_CUSTOM = "custom_protocols_agents"

_ALL_FEATURES = frozenset(
    {FEATURE_PREMIUM_PROTOCOLS, FEATURE_KNOWLEDGE_GRAPH, FEATURE_CUSTOM}
)


def _enforce() -> bool:
    """Read the kill switch at call time so tests/env flips need no reload."""
    return os.getenv("ENTITLEMENTS_ENFORCE", "0").lower() in ("1", "true", "yes")


# Curated protocols available on the free plan: cheap, single-pass shapes.
# Everything else requires the premium_protocols feature.
_DEFAULT_FREE_PROTOCOLS = (
    "p00_direct,p01_single_agent,p03_parallel_synthesis,p07_wicked_questions,"
    "p08_min_specs,p14_one_two_four_all,p15_what_so_what_now_what"
)
FREE_PROTOCOL_KEYS: frozenset[str] = frozenset(
    k.strip()
    for k in (os.getenv("CE_FREE_PROTOCOLS") or _DEFAULT_FREE_PROTOCOLS).split(",")
    if k.strip()
)


@dataclass(frozen=True)
class Entitlements:
    """Resolved limits for one tenant. ``None`` limits mean unlimited."""

    plan: str  # free | pro | enterprise | internal
    runs_per_month: int | None
    run_cost_ceiling_usd: float | None
    features: frozenset[str]


def _env_int(name: str, default: str) -> int:
    try:
        return int(os.getenv(name) or default)
    except ValueError:
        return int(default)


def _env_float(name: str, default: str) -> float:
    try:
        return float(os.getenv(name) or default)
    except ValueError:
        return float(default)


def plan_defaults(plan: str) -> Entitlements:
    """Map a plan slug to its limits. Unknown slugs resolve to free."""
    if plan == "internal":
        return Entitlements("internal", None, None, _ALL_FEATURES)
    if plan == "enterprise":
        return Entitlements(
            "enterprise",
            None,
            _env_float("CE_ENT_RUN_COST_CAP", "25.0"),
            _ALL_FEATURES,
        )
    if plan == "pro":
        return Entitlements(
            "pro",
            _env_int("CE_PRO_RUNS_PER_MONTH", "100"),
            _env_float("CE_PRO_RUN_COST_CAP", "5.0"),
            _ALL_FEATURES,
        )
    return Entitlements(
        "free",
        _env_int("CE_FREE_RUNS_PER_MONTH", "5"),
        _env_float("CE_FREE_RUN_COST_CAP", "0.50"),
        frozenset(),
    )


# Legacy ce-railway template fallback (Organization.public_metadata.tier).
_LEGACY_TIER_TO_PLAN = {1: "free", 2: "pro", 3: "enterprise"}


def entitlements_from_auth(ctx: ClerkAuthContext | None) -> Entitlements:
    """Resolve entitlements from an auth context (None = trusted internal caller)."""
    if ctx is None:
        return plan_defaults("internal")
    if ctx.plan:
        base = plan_defaults(ctx.plan if ctx.plan in ("pro", "enterprise") else "free")
        # The fea claim is authoritative when present -- it reflects the exact
        # features attached to the org's plan in the Clerk dashboard.
        features = ctx.features if ctx.features else base.features
        return Entitlements(
            base.plan, base.runs_per_month, base.run_cost_ceiling_usd, features
        )
    if ctx.tier:
        return plan_defaults(_LEGACY_TIER_TO_PLAN.get(ctx.tier, "free"))
    return plan_defaults("free")


@dataclass(frozen=True)
class TenantEntitlements:
    """Tenant slug + resolved entitlements, as returned by ``get_entitlements``."""

    tenant_slug: str
    entitlements: Entitlements
    auth: ClerkAuthContext | None


async def get_entitlements(request: Request) -> TenantEntitlements:
    """FastAPI dependency: resolve tenant + entitlements for this request.

    Bearer token present -> validated Clerk claims are authoritative (invalid
    tokens fail with 401, no org fails with 400 -- same contract as
    ``resolve_tenant``). No Bearer token -> API-key / local-dev fallback path:
    ``resolve_tenant`` picks the tenant and the caller is treated as internal.
    """
    if _bearer_token(request):
        ctx = await get_auth(request)
        slug = _canonicalize_slug(ctx.require_org())
        return TenantEntitlements(slug, entitlements_from_auth(ctx), ctx)
    slug = await resolve_tenant(request)
    return TenantEntitlements(slug, entitlements_from_auth(None), None)


def month_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Return [start, end) of the current UTC calendar month.

    v1 quota window is the calendar month, not the Stripe billing anchor.
    """
    now = now or datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def runs_used_this_month(session: Session, tenant_slug: str) -> int:
    """Count quota-consuming runs for a tenant in the current month.

    Failed runs don't burn quota -- the customer got nothing for them.
    """
    start, end = month_window()
    count = session.exec(
        select(func.count())
        .select_from(Run)
        .where(Run.tenant_slug == tenant_slug)
        .where(Run.started_at >= start)
        .where(Run.started_at < end)
        .where(Run.status != "failed")
    ).one()
    return int(count)


async def require_run_admission(
    te: TenantEntitlements = Depends(get_entitlements),
    session: Session = Depends(get_session),
) -> TenantEntitlements:
    """Dependency for money-spending endpoints: 402 when over the monthly quota."""
    limit = te.entitlements.runs_per_month
    if limit is not None:
        used = runs_used_this_month(session, te.tenant_slug)
        if used >= limit:
            detail = {
                "code": "quota_exceeded",
                "message": (
                    f"Monthly run limit reached ({used} of {limit} on the "
                    f"{te.entitlements.plan} plan). Upgrade to keep running."
                ),
                "plan": te.entitlements.plan,
                "used": used,
                "limit": limit,
                "upgrade_url": "/billing",
            }
            if _enforce():
                raise HTTPException(status_code=402, detail=detail)
            logger.warning("ENTITLEMENTS(dry-run) would block run: %s", detail)
    return te


def require_feature(feature: str):
    """Dependency factory: 403 when the org's plan lacks ``feature``."""

    async def _dep(
        te: TenantEntitlements = Depends(get_entitlements),
    ) -> TenantEntitlements:
        if feature not in te.entitlements.features:
            detail = {
                "code": "feature_required",
                "feature": feature,
                "plan": te.entitlements.plan,
                "message": "This capability requires the Pro plan.",
                "upgrade_url": "/billing",
            }
            if _enforce():
                raise HTTPException(status_code=403, detail=detail)
            logger.warning("ENTITLEMENTS(dry-run) would block feature: %s", detail)
        return te

    return _dep


def check_protocol_allowed(protocol_key: str, te: TenantEntitlements) -> None:
    """403 when a premium protocol is requested without the feature."""
    if protocol_key in FREE_PROTOCOL_KEYS:
        return
    if FEATURE_PREMIUM_PROTOCOLS in te.entitlements.features:
        return
    detail = {
        "code": "feature_required",
        "feature": FEATURE_PREMIUM_PROTOCOLS,
        "protocol_key": protocol_key,
        "plan": te.entitlements.plan,
        "message": "This protocol requires the Pro plan.",
        "upgrade_url": "/billing",
    }
    if _enforce():
        raise HTTPException(status_code=403, detail=detail)
    logger.warning("ENTITLEMENTS(dry-run) would block protocol: %s", detail)


__all__ = [
    "FEATURE_CUSTOM",
    "FEATURE_KNOWLEDGE_GRAPH",
    "FEATURE_PREMIUM_PROTOCOLS",
    "FREE_PROTOCOL_KEYS",
    "Entitlements",
    "TenantEntitlements",
    "check_protocol_allowed",
    "entitlements_from_auth",
    "get_entitlements",
    "month_window",
    "plan_defaults",
    "require_feature",
    "require_run_admission",
    "runs_used_this_month",
]
