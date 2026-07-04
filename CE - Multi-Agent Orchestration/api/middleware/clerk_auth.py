"""Clerk JWT verification + tenant context resolution.

Bridges the Next.js portal (cardinal-portal) with the Railway FastAPI engine.
The portal sends Clerk-issued JWTs in the Authorization header; this module
validates them against Clerk's published JWKS and extracts claims from either
token format:

**Default session token (v2)** — the current portal format. Org claims are
nested under ``o`` (``o.slg`` slug, ``o.id``, ``o.rol`` role) and Clerk
Billing state rides in session-tied claims:

- ``pla``  -- active plan, e.g. ``"o:pro"`` (``o:`` = org-payer)
- ``fea``  -- enabled features, e.g. ``"o:premium_protocols,o:knowledge_graph"``

**Legacy ``ce-railway`` JWT template** — flat ``org_slug`` / ``org_role`` /
``tier`` (1/2/3 from Organization.public_metadata.tier) claims. Supported as
a fallback until the template is retired; ``pla``/``fea`` cannot appear in
custom templates (Clerk forbids session-tied claims there).

Set ``CLERK_JWKS_URL`` and (optionally) ``CLERK_AUDIENCE`` in env. If unset,
all auth-required endpoints fail closed with 503 (server misconfigured).
Leave ``CLERK_AUDIENCE`` unset for default session tokens (they carry ``azp``,
not ``aud``).
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import httpx
from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

JWKS_TTL_SECONDS = 3600
_jwks_cache: dict[str, tuple[float, dict[str, Any]]] = {}


@dataclass(frozen=True)
class ClerkAuthContext:
    """Resolved Clerk JWT claims. Attach to ``request.state.auth``."""

    user_id: str
    org_id: str | None
    org_slug: str | None
    org_role: str | None
    tier: int | None
    plan: str | None
    features: frozenset[str]
    raw_claims: dict[str, Any]

    def require_org(self) -> str:
        if not self.org_slug:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active organization on this session. Pick or create one first.",
            )
        return self.org_slug


def _get_jwks(jwks_url: str) -> dict[str, Any]:
    now = time.time()
    cached = _jwks_cache.get(jwks_url)
    if cached and now - cached[0] < JWKS_TTL_SECONDS:
        return cached[1]
    try:
        r = httpx.get(jwks_url, timeout=5.0)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cannot fetch Clerk JWKS: {exc}",
        ) from exc
    _jwks_cache[jwks_url] = (now, data)
    return data


def _decode_token(token: str, jwks_url: str, audience: str | None) -> dict[str, Any]:
    jwks = _get_jwks(jwks_url)
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Malformed token: {exc}"
        )

    kid = unverified_header.get("kid")
    key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signing key not found in JWKS",
        )

    options = {"verify_aud": bool(audience)}
    try:
        return jwt.decode(
            token,
            key,
            algorithms=[key.get("alg", "RS256")],
            audience=audience,
            options=options,
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {exc}"
        )


@lru_cache(maxsize=1)
def _config() -> tuple[str | None, str | None]:
    return os.environ.get("CLERK_JWKS_URL"), os.environ.get("CLERK_AUDIENCE")


def _parse_claims(claims: dict[str, Any]) -> ClerkAuthContext:
    """Build a ClerkAuthContext from either token format.

    Default session tokens (v2) nest org claims under ``o`` and carry billing
    state in ``pla`` (plan) / ``fea`` (features). Legacy ``ce-railway``
    template tokens use flat ``org_slug``/``org_role``/``tier`` claims.
    """
    o = claims.get("o") or {}
    is_v2 = bool(o) or claims.get("v") == 2

    if is_v2:
        org_id = o.get("id")
        org_slug = o.get("slg")
        org_role = f"org:{o['rol']}" if o.get("rol") else None
    else:
        org_id = claims.get("org_id")
        org_slug = claims.get("org_slug")
        org_role = claims.get("org_role")

    # pla: "o:pro" -> "pro". Only org-payer plans count (org = tenant = payer).
    plan: str | None = None
    pla = claims.get("pla")
    if isinstance(pla, str) and ":" in pla:
        payer, _, slug = pla.partition(":")
        if "o" in payer and slug:
            plan = slug

    # fea: "o:premium_protocols,uo:knowledge_graph" -> org-payer features.
    features: set[str] = set()
    fea = claims.get("fea")
    if isinstance(fea, str):
        for item in fea.split(","):
            payer, _, feat = item.strip().partition(":")
            if feat and "o" in payer:
                features.add(feat)

    # Legacy tier claim (from Organization.public_metadata.tier).
    tier_raw = claims.get("tier")
    tier: int | None
    try:
        tier = (
            int(tier_raw)
            if tier_raw is not None and str(tier_raw).strip() != ""
            else None
        )
    except (TypeError, ValueError):
        tier = None

    return ClerkAuthContext(
        user_id=str(claims.get("sub", "")),
        org_id=org_id,
        org_slug=org_slug,
        org_role=org_role,
        tier=tier,
        plan=plan,
        features=frozenset(features),
        raw_claims=claims,
    )


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("Authorization") or ""
    if not header.lower().startswith("bearer "):
        return None
    return header.split(" ", 1)[1].strip() or None


async def get_auth(request: Request) -> ClerkAuthContext:
    """FastAPI dependency: validate Clerk JWT, return context. 401 if missing/invalid."""
    existing = getattr(request.state, "auth", None)
    if isinstance(existing, ClerkAuthContext):
        return existing

    jwks_url, audience = _config()
    if not jwks_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CLERK_JWKS_URL is not configured. Cannot validate JWTs.",
        )

    token = _bearer_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization: Bearer <jwt> header",
        )

    claims = _decode_token(token, jwks_url, audience)
    ctx = _parse_claims(claims)
    request.state.auth = ctx
    return ctx


async def get_auth_with_org(
    ctx: ClerkAuthContext = Depends(get_auth),
) -> ClerkAuthContext:
    """Same as ``get_auth`` but also requires an active org. Use for tenant-scoped endpoints."""
    ctx.require_org()
    return ctx


# ---------------------------------------------------------------------------
# Backward-compatible tenant resolution
# ---------------------------------------------------------------------------
#
# ``resolve_tenant`` is the bridge between authenticated portal requests and
# explicitly trusted non-portal callers (local CLI, curl, scripts with API key):
#
#   1. If a Bearer token is present -> validate it and require ``org_slug``.
#   2. Else if ``CE_DEV_TENANT`` env var is set -> use that.
#   3. Else fall back to ``DEFAULT_TENANT`` for trusted non-portal calls.
#
# ``DEFAULT_TENANT`` is "local-dev" by default, so unauth'd callers write to an
# isolated tenant and cannot silently pollute CE's production state. To restore
# the old behavior (fallback to CE's own tenant), set ``CE_ALLOW_PROD=1`` in
# the environment -- Railway does this, local dev does not.
#
# Production: set CLERK_JWKS_URL + CE_ALLOW_PROD=1 on Railway. Endpoints that
# should always require auth (admin, billing) use ``get_auth_with_org``
# directly instead of ``resolve_tenant``.

DEFAULT_TENANT = (
    "cardinal-element" if os.environ.get("CE_ALLOW_PROD") == "1" else "local-dev"
)

# Clerk auto-appends a 16+ digit numeric ID to org slugs when the base slug is
# already taken in the instance (e.g. "cardinal-element-1776752029963075226").
# We canonicalize those to their base slug so runs persisted under either
# form are accessible from either session variant.
import re as _re

_CLERK_SUFFIX_RE = _re.compile(r"^(.+)-(\d{10,})$")


def _canonicalize_slug(slug: str) -> str:
    """Strip Clerk's auto-appended long numeric suffix."""
    if not slug:
        return slug
    m = _CLERK_SUFFIX_RE.match(slug)
    return m.group(1) if m else slug


async def resolve_tenant(request: Request) -> str:
    """Resolve the tenant slug for a request.

    A present Bearer token is authoritative: invalid tokens or sessions without
    an active organization fail instead of silently falling back to a default
    tenant. Requests without a Bearer token keep the API-key/local-script
    fallback path.
    """
    # 1. If the caller supplies a JWT, it must be valid and organization-scoped.
    token = _bearer_token(request)
    if token:
        ctx = await get_auth(request)
        return _canonicalize_slug(ctx.require_org())

    # 2. Env override (local dev convenience)
    env_slug = os.environ.get("CE_DEV_TENANT")
    if env_slug:
        return _canonicalize_slug(env_slug)

    # 3. Default to CE's own tenant
    return DEFAULT_TENANT


__all__ = [
    "ClerkAuthContext",
    "DEFAULT_TENANT",
    "get_auth",
    "get_auth_with_org",
    "resolve_tenant",
]
