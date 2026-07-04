"""Per-tenant Corrections — user-provided course corrections written to the graph.

A Correction attaches to a scope (global / client / engagement / protocol /
agent / decision) and is surfaced to agents via ``context_assembler`` before
every future run that matches the scope.

This is the "once, then forever" feedback channel. Say "don't pitch Acme
aggressive sales tactics" once, and every future run touching Acme loads
that correction as institutional memory.
"""

from __future__ import annotations

import logging
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.entitlements import (
    FEATURE_KNOWLEDGE_GRAPH,
    TenantEntitlements,
    require_feature,
)
from api.middleware.clerk_auth import get_auth_with_org, resolve_tenant

_require_graph = require_feature(FEATURE_KNOWLEDGE_GRAPH)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/corrections", tags=["corrections"])

ALLOWED_SCOPES = {"global", "client", "engagement", "protocol", "agent", "decision"}


class CorrectionIn(BaseModel):
    text: str
    scope: Literal["global", "client", "engagement", "protocol", "agent", "decision"]
    target_id: str | None = None
    reason: str | None = None


class CorrectionOut(BaseModel):
    id: str
    text: str
    scope: str
    target_id: str | None
    reason: str | None
    given_by: str
    given_at: int | None
    valid_to: int | None


def _get_queries(tenant_slug: str):
    try:
        from ce_graph.falkor_client import FalkorClient
        from ce_graph.queries import GraphQueries
        from ce_graph.tenancy import load_tenant
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ce-graph unavailable: {exc}",
        )
    try:
        tenant = load_tenant(tenant_slug)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_slug}' not provisioned in ce-graph.",
        )
    return GraphQueries(FalkorClient(tenant=tenant))


@router.get("")
async def list_corrections(
    active_only: bool = True,
    tenant_slug: str = Depends(resolve_tenant),
    _feature: TenantEntitlements = Depends(_require_graph),
) -> dict:
    q = _get_queries(tenant_slug)
    rows = q.list_corrections(active_only=active_only)
    return {"tenant_slug": tenant_slug, "corrections": rows, "count": len(rows)}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_correction(
    payload: CorrectionIn,
    auth=Depends(get_auth_with_org),
    _feature: TenantEntitlements = Depends(_require_graph),
) -> CorrectionOut:
    if payload.scope != "global" and not payload.target_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Correction scope '{payload.scope}' requires a target_id "
            "(e.g. client name, protocol code, agent key, decision id).",
        )
    q = _get_queries(auth.org_slug or "cardinal-element")
    correction_id = f"cor_{uuid.uuid4().hex[:16]}"
    q.write_correction(
        correction_id=correction_id,
        text=payload.text,
        scope=payload.scope,
        target_id=payload.target_id,
        reason=payload.reason,
        given_by=auth.user_id or "unknown",
    )
    logger.info(
        "Correction %s created: scope=%s target=%s by=%s",
        correction_id,
        payload.scope,
        payload.target_id,
        auth.user_id,
    )
    return CorrectionOut(
        id=correction_id,
        text=payload.text,
        scope=payload.scope,
        target_id=payload.target_id,
        reason=payload.reason,
        given_by=auth.user_id or "unknown",
        given_at=None,
        valid_to=None,
    )


@router.delete("/{correction_id}")
async def retire_correction(
    correction_id: str,
    tenant_slug: str = Depends(resolve_tenant),
    _feature: TenantEntitlements = Depends(_require_graph),
) -> dict:
    """Retire a correction (sets valid_to=now). Kept in history for audit."""
    q = _get_queries(tenant_slug)
    q.retire_correction(correction_id=correction_id)
    logger.info("Correction %s retired for tenant %s", correction_id, tenant_slug)
    return {"ok": True, "id": correction_id, "retired": True}
