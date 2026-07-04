"""Per-tenant knowledge graph endpoints.

Thin HTTP wrappers around ``ce-graph``:
  GET  /api/graph/stats      -- node counts per label for this tenant's graph
  GET  /api/graph/health     -- whether FalkorDB is reachable
  POST /api/graph/backfill   -- kick off Notion / Granola backfill (background)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.middleware.clerk_auth import resolve_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/graph", tags=["graph"])


class BackfillRequest(BaseModel):
    sources: list[Literal["notion", "granola"]] = Field(default_factory=lambda: ["notion", "granola"])
    since: str | None = None  # ISO-8601 (e.g. "2025-01-01"); optional
    limit: int | None = None  # cap pages/meetings ingested per source


def _get_graph_queries(tenant_slug: str):
    """Import ce-graph lazily (not everyone runs it locally)."""
    try:
        from ce_graph.falkor_client import FalkorClient
        from ce_graph.queries import GraphQueries
        from ce_graph.tenancy import load_tenant
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ce-graph not installed in this environment: {exc}",
        )
    try:
        tenant = load_tenant(tenant_slug)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_slug}' not provisioned in ce-graph. "
                   f"Run cegraph init --tenant {tenant_slug} first.",
        )
    return GraphQueries(FalkorClient(tenant=tenant))


@router.get("/stats")
async def graph_stats(tenant_slug: str = Depends(resolve_tenant)) -> dict:
    """Return node counts per label in this tenant's graph."""
    try:
        q = _get_graph_queries(tenant_slug)
        counts = q.graph_stats()
        populated = {label: n for label, n in counts.items() if n > 0}
        total = sum(counts.values())
        return {
            "tenant_slug": tenant_slug,
            "graph_name": q.client.graph_name,
            "total_nodes": total,
            "counts": populated,
            "all_labels": counts,  # includes zeros
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("graph_stats failed for %s: %s", tenant_slug, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"FalkorDB unreachable or query failed: {exc}",
        )


@router.get("/nodes")
async def graph_subgraph(
    limit: int = 500,
    tenant_slug: str = Depends(resolve_tenant),
) -> dict:
    """Return a node + edge subgraph for interactive visualization.

    Returns up to ``limit`` highest-degree nodes (sorted by connection count)
    plus the edges between them. Tenant-scoped via the Clerk JWT middleware.
    """
    if limit <= 0 or limit > 5000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit must be between 1 and 5000",
        )
    try:
        q = _get_graph_queries(tenant_slug)
        sub = q.subgraph(limit=limit)
        return {
            "tenant_slug": tenant_slug,
            "graph_name": q.client.graph_name,
            "limit": limit,
            "node_count": len(sub["nodes"]),
            "edge_count": len(sub["edges"]),
            **sub,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("graph_subgraph failed for %s: %s", tenant_slug, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"FalkorDB unreachable or query failed: {exc}",
        )


@router.get("/health")
async def graph_health() -> dict:
    """Unauthenticated probe. Returns whether ce-graph/FalkorDB is operational."""
    try:
        from ce_graph.falkor_client import FalkorClient
        c = FalkorClient()
        c.query("RETURN 1")
        return {"ok": True, "ce_graph": True, "falkordb": True}
    except Exception as exc:
        return {"ok": False, "ce_graph": True, "falkordb": False, "error": str(exc)[:200]}


def _parse_since(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        # Accept "2025-01-01" or full ISO timestamps.
        if len(raw) == 10:
            return datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid 'since' (use ISO-8601, e.g. 2025-01-01): {exc}",
        )


async def _run_backfill(
    tenant_slug: str,
    sources: list[str],
    since: datetime | None,
    limit: int | None,
) -> None:
    """Background worker — runs each requested backfill sequentially.

    Each step is wrapped in try/except so one failing source doesn't kill the
    others. Any module-level errors (missing API keys, etc.) are logged.
    """
    for src in sources:
        try:
            if src == "notion":
                from ce_graph.scripts.backfill_notion import backfill as notion_backfill
                logger.info(
                    "graph_backfill.start tenant=%s source=notion since=%s limit=%s",
                    tenant_slug, since, limit,
                )
                rc = await notion_backfill(
                    since=since, dry_run=False, limit=limit, tenant_slug=tenant_slug,
                )
                logger.info(
                    "graph_backfill.done tenant=%s source=notion rc=%s", tenant_slug, rc,
                )
            elif src == "granola":
                from ce_graph.scripts.backfill_granola import backfill as granola_backfill
                logger.info(
                    "graph_backfill.start tenant=%s source=granola since=%s limit=%s",
                    tenant_slug, since, limit,
                )
                rc = await granola_backfill(
                    since=since, dry_run=False, limit=limit, tenant_slug=tenant_slug,
                )
                logger.info(
                    "graph_backfill.done tenant=%s source=granola rc=%s", tenant_slug, rc,
                )
        except Exception as exc:
            logger.warning(
                "graph_backfill.failed tenant=%s source=%s err=%s",
                tenant_slug, src, exc,
            )


@router.post("/backfill", status_code=status.HTTP_202_ACCEPTED)
async def graph_backfill(
    payload: BackfillRequest,
    background_tasks: BackgroundTasks,
    tenant_slug: str = Depends(resolve_tenant),
) -> dict:
    """Kick off a Notion + Granola backfill for this tenant.

    Returns immediately (202) and runs the ingest in the background. Tail logs
    for ``graph_backfill.start/done/failed`` lines to follow progress.
    """
    if not payload.sources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one source must be requested.",
        )
    since = _parse_since(payload.since)

    # Verify the tenant is provisioned before scheduling work.
    try:
        from ce_graph.tenancy import load_tenant
        load_tenant(tenant_slug)
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ce-graph not installed in this environment: {exc}",
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_slug}' not provisioned. "
                   f"Run cegraph init --tenant {tenant_slug} first.",
        )

    # Schedule on FastAPI's background runner. Because the scripts are async,
    # wrap them in a coroutine and let asyncio dispatch.
    async def _runner():
        await _run_backfill(tenant_slug, list(payload.sources), since, payload.limit)

    background_tasks.add_task(asyncio.create_task, _runner())
    return {
        "ok": True,
        "tenant_slug": tenant_slug,
        "sources": payload.sources,
        "since": payload.since,
        "limit": payload.limit,
        "status": "scheduled",
    }
