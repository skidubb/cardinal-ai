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
from api.middleware.clerk_auth import resolve_tenant
from api.models import Run

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("")
async def tenant_usage(
    session: Session = Depends(get_session),
    tenant_slug: str = Depends(resolve_tenant),
) -> dict:
    """Return per-tenant aggregate metrics across all runs."""
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

    return {
        "tenant_slug": tenant_slug,
        "total_runs": total_runs,
        "total_cost_usd": round(total_cost, 6),
        "last_run_at": last_run.isoformat() if last_run else None,
        "by_status": by_status,
        "completed_runs": completed["count"],
        "completed_cost_usd": round(completed["cost_usd"], 6),
    }
