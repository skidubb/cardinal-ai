"""Clerk webhook handler.

Clerk fires webhook events (organization.created, user.created, etc.) signed
with Svix. This router verifies the signature and provisions a fresh
``ce-graph`` tenant for every new Organization.

Wire endpoint in Clerk dashboard:
    URL:    https://<your-railway-app>/api/webhooks/clerk
    Events: organization.created, organization.updated, organization.deleted
    Secret: copy "Signing Secret" -> set CLERK_WEBHOOK_SECRET in env
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import sys

from fastapi import APIRouter, HTTPException, Request, status
from svix.webhooks import Webhook, WebhookVerificationError

from api.middleware.clerk_auth import _canonicalize_slug


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$")


def _slugify(name: str) -> str:
    """Best-effort slug from an Organization name (Clerk usually provides .slug already)."""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9-]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:48] or "tenant"


def _cegraph_python() -> str | None:
    """Interpreter that can run the cegraph CLI.

    Prefer the dedicated ce-graph venv when present (local dev, keeps
    Graphiti/FalkorDB deps out of the orchestration runtime). Fall back to
    this process's interpreter when ce_graph is installed in it (the Docker
    image pip-installs ce-graph into the main environment).
    """
    repo_root = os.environ.get(
        "CE_REPO_ROOT", "/Users/scottewalt/Documents/CE - AGENTS"
    )
    venv_python = f"{repo_root}/ce-graph/venv/bin/python"
    if os.path.exists(venv_python):
        return venv_python
    try:
        import ce_graph  # noqa: F401
    except ImportError:
        return None
    return sys.executable


async def _provision_tenant_graph(slug: str) -> None:
    """Provision a fresh ce-graph tenant: create config (if missing) + seed protocols.

    Runs the cegraph CLI as a subprocess; ce_graph resolves the repo root and
    tenants dir from its own module location, so no cwd is needed. The CLI is
    idempotent so re-firing the webhook is safe.
    """
    python = _cegraph_python()
    if python is None:
        logger.warning(
            "No interpreter with ce_graph available; skipping graph provisioning "
            "for %s. Run `cd ce-graph && python -m venv venv && pip install -e .` "
            "or install ce-graph into this environment.",
            slug,
        )
        return

    create = await asyncio.create_subprocess_exec(
        python,
        "-m",
        "ce_graph.cli",
        "create",
        slug,
        "--display",
        slug.replace("-", " ").title(),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await create.communicate()
    if create.returncode != 0 and b"already exists" not in err:
        logger.warning("cegraph create failed for %s: %s", slug, err.decode()[:300])

    init = await asyncio.create_subprocess_exec(
        python,
        "-m",
        "ce_graph.cli",
        "init",
        "--tenant",
        slug,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await init.communicate()
    if init.returncode == 0:
        logger.info("ce-graph provisioned for tenant %s", slug)
    else:
        logger.error("cegraph init failed for %s: %s", slug, err.decode()[:300])


def _verify_signature(request_body: bytes, headers: dict) -> dict:
    secret = os.environ.get("CLERK_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CLERK_WEBHOOK_SECRET not configured",
        )
    wh = Webhook(secret)
    try:
        return wh.verify(request_body, headers)
    except WebhookVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Clerk webhook signature: {exc}",
        )


@router.post("/clerk")
async def clerk_webhook(request: Request) -> dict:
    body = await request.body()
    headers = {
        "svix-id": request.headers.get("svix-id", ""),
        "svix-timestamp": request.headers.get("svix-timestamp", ""),
        "svix-signature": request.headers.get("svix-signature", ""),
    }
    if not all(headers.values()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required svix-* headers",
        )

    payload = _verify_signature(body, headers)
    event_type = payload.get("type", "")
    data = payload.get("data", {}) or {}

    logger.info(
        "Clerk webhook: %s (org=%s user=%s)",
        event_type,
        data.get("id"),
        data.get("user_id"),
    )

    if event_type == "organization.created":
        slug = (data.get("slug") or _slugify(data.get("name", ""))).lower()
        # Match resolve_tenant: strip Clerk's auto-appended numeric suffix so
        # the provisioned tenant file is the one the API actually looks up.
        slug = _canonicalize_slug(slug)
        if not SLUG_RE.match(slug):
            logger.warning("Skipping invalid org slug: %s", slug)
            return {"ok": True, "skipped": "invalid_slug"}
        asyncio.create_task(_provision_tenant_graph(slug))
        return {"ok": True, "provisioning": slug}

    if event_type == "organization.deleted":
        slug = data.get("slug") or "(no slug)"
        logger.warning(
            "organization.deleted for slug=%s. Graph NOT dropped automatically. "
            "Run `cegraph drop --tenant %s --yes` to clean up.",
            slug,
            slug,
        )
        return {"ok": True, "manual_cleanup_required": slug}

    return {"ok": True, "event": event_type}


@router.get("/clerk/health")
async def clerk_webhook_health() -> dict:
    return {
        "ok": True,
        "secret_configured": bool(os.environ.get("CLERK_WEBHOOK_SECRET")),
    }
