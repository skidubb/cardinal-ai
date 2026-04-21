"""Per-tenant knowledge graph endpoints.

Thin HTTP wrappers around ``ce-graph``:
  GET /api/graph/stats      -- node counts per label for this tenant's graph
  GET /api/graph/health     -- whether FalkorDB is reachable
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from api.middleware.clerk_auth import resolve_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/graph", tags=["graph"])


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
