"""Per-tenant usage + cost summary.

Aggregates the existing ``runs`` table (no new tables). Returns everything
the dashboard + admin panel need to surface how much LLM spend + run volume
a tenant has accrued.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlmodel import Session, func, select

from api.database import get_session
from api.entitlements import TenantEntitlements, get_entitlements, month_window
from api.models import Run

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("")
async def tenant_usage(
    session: Session = Depends(get_session),
    te: TenantEntitlements = Depends(get_entitlements),
) -> dict:
    """Return per-tenant aggregate metrics: all-time plus current billing period.

    The period fields power the portal's quota meter ("X of Y runs used this
    month"). The period is the UTC calendar month; failed runs don't count.
    """
    tenant_slug = te.tenant_slug
    rows = list(
        session.exec(
            select(
                func.count(Run.id),
                func.coalesce(func.sum(Run.cost_usd), 0.0),
                func.max(Run.started_at),
                Run.status,
            )
            .where(Run.tenant_slug == tenant_slug)
            .group_by(Run.status)
        ).all()
    )

    by_status: dict[str, dict] = {}
    total_runs = 0
    total_cost = 0.0
    last_run: datetime | None = None
    for count, cost, last_at, status_value in rows:
        by_status[status_value] = {"count": int(count), "cost_usd": float(cost)}
        total_runs += int(count)
        total_cost += float(cost)
        if last_at and (last_run is None or last_at > last_run):
            last_run = last_at

    completed = by_status.get("completed", {"count": 0, "cost_usd": 0.0})

    # Current billing period (UTC calendar month). Failed runs don't burn quota.
    start, end = month_window()
    period_row = session.exec(
        select(
            func.count(Run.id),
            func.coalesce(func.sum(Run.cost_usd), 0.0),
        )
        .where(Run.tenant_slug == tenant_slug)
        .where(Run.started_at >= start)
        .where(Run.started_at < end)
        .where(Run.status != "failed")
    ).one()
    period_runs = int(period_row[0])
    period_cost = float(period_row[1])

    limit = te.entitlements.runs_per_month

    return {
        "tenant_slug": tenant_slug,
        "total_runs": total_runs,
        "total_cost_usd": round(total_cost, 6),
        "last_run_at": last_run.isoformat() if last_run else None,
        "by_status": by_status,
        "completed_runs": completed["count"],
        "completed_cost_usd": round(completed["cost_usd"], 6),
        "plan": te.entitlements.plan,
        "features": sorted(te.entitlements.features),
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "period_runs": period_runs,
        "period_cost_usd": round(period_cost, 6),
        "runs_limit": limit,
        "runs_remaining": max(0, limit - period_runs) if limit is not None else None,
        "run_cost_cap_usd": te.entitlements.run_cost_ceiling_usd,
    }
