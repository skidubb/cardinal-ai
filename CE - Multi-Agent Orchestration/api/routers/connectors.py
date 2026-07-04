"""Per-tenant connector status + backfill trigger.

Connectors fall into two auth camps:

  * **Direct-API** (HubSpot currently) -- token lives in Railway env, we run
    the cegraph CLI as a subprocess to ingest.
  * **MCP-driven** (Notion, Granola, Gmail, Slack, Drive) -- OAuth-authenticated
    in the caller's Claude environment. We cannot execute from Railway; instead
    we return the instruction to run the ``ce-graph-backfill`` Claude agent.

Both return a consistent ``BackfillResponse`` so the portal UI doesn't have
to branch.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.entitlements import (
    FEATURE_KNOWLEDGE_GRAPH,
    TenantEntitlements,
    require_feature,
)
from api.middleware.clerk_auth import resolve_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/connectors", tags=["connectors"])


class BackfillRequest(BaseModel):
    connector: str
    since: str | None = None
    limit: int | None = None
    dry_run: bool = False


class BackfillResponse(BaseModel):
    mode: Literal["direct_api", "mcp_runbook"]
    connector: str
    tenant_slug: str
    status: Literal["queued", "runbook_only"]
    message: str
    runbook: str | None = None


MCP_CONNECTORS = {"notion", "granola", "google_drive", "slack", "gmail"}
DIRECT_API_CONNECTORS = {"hubspot"}


def _load_tenant_connectors(tenant_slug: str) -> dict:
    try:
        from ce_graph.tenancy import load_tenant
    except ImportError:
        return {}
    try:
        return load_tenant(tenant_slug).connectors or {}
    except FileNotFoundError:
        return {}


@router.get("/status")
async def connectors_status(tenant_slug: str = Depends(resolve_tenant)) -> dict:
    """Return which connectors are configured for this tenant."""
    configured = _load_tenant_connectors(tenant_slug)
    out: list[dict] = []
    for name in sorted(MCP_CONNECTORS | DIRECT_API_CONNECTORS):
        cfg = configured.get(name, {}) or {}
        out.append(
            {
                "name": name,
                "mode": "direct_api" if name in DIRECT_API_CONNECTORS else "mcp_driven",
                "enabled": bool(cfg.get("enabled", False)),
                "auth": cfg.get("auth", "mcp" if name in MCP_CONNECTORS else "token"),
                "notes": cfg.get("notes"),
            }
        )
    return {"tenant_slug": tenant_slug, "connectors": out}


async def _run_cegraph_backfill(
    tenant_slug: str,
    connector: str,
    since: str | None,
    limit: int | None,
    dry_run: bool,
) -> None:
    repo_root = os.environ.get(
        "CE_REPO_ROOT", "/Users/scottewalt/Documents/CE - AGENTS"
    )
    venv_python = f"{repo_root}/ce-graph/venv/bin/python"
    if not os.path.exists(venv_python):
        logger.warning(
            "ce-graph venv missing; cannot run direct-API backfill for %s", tenant_slug
        )
        return
    args = [
        venv_python,
        "-m",
        f"ce_graph.scripts.backfill_{connector}",
        "--tenant",
        tenant_slug,
    ]
    if since:
        args += ["--since", since]
    if limit:
        args += ["--limit", str(limit)]
    if dry_run:
        args += ["--dry-run"]
    logger.info("Starting backfill: %s", " ".join(args))
    proc = await asyncio.create_subprocess_exec(
        *args,
        cwd=f"{repo_root}/ce-graph",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if proc.returncode == 0:
        logger.info("Backfill %s completed for %s", connector, tenant_slug)
    else:
        logger.error(
            "Backfill %s failed for %s: %s", connector, tenant_slug, err.decode()[:500]
        )


@router.post("/start")
async def start_connector(
    payload: BackfillRequest,
    tenant_slug: str = Depends(resolve_tenant),
    _feature: TenantEntitlements = Depends(require_feature(FEATURE_KNOWLEDGE_GRAPH)),
) -> BackfillResponse:
    name = payload.connector.lower()
    if name not in (MCP_CONNECTORS | DIRECT_API_CONNECTORS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown connector: {name}. Supported: "
            f"{sorted(MCP_CONNECTORS | DIRECT_API_CONNECTORS)}",
        )

    if name in DIRECT_API_CONNECTORS:
        asyncio.create_task(
            _run_cegraph_backfill(
                tenant_slug, name, payload.since, payload.limit, payload.dry_run
            )
        )
        return BackfillResponse(
            mode="direct_api",
            connector=name,
            tenant_slug=tenant_slug,
            status="queued",
            message=f"Backfill started for {name}. Check /api/graph/stats in ~30s.",
        )

    since_clause = f", since {payload.since}" if payload.since else ""
    limit_clause = f", limit {payload.limit}" if payload.limit else ""
    dry_clause = ", dry-run" if payload.dry_run else ""
    runbook = (
        f"In Claude Code, invoke:\n"
        f"  Task tool, subagent_type: ce-graph-backfill\n"
        f'  Prompt: "backfill {name} for tenant {tenant_slug}{since_clause}{limit_clause}{dry_clause}"\n'
    )
    return BackfillResponse(
        mode="mcp_runbook",
        connector=name,
        tenant_slug=tenant_slug,
        status="runbook_only",
        message=(
            f"{name} is MCP-authenticated. Railway can't trigger it directly -- "
            "run the backfill agent inside Claude Code instead."
        ),
        runbook=runbook,
    )
