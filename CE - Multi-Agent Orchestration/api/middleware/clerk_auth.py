"""Clerk JWT verification + tenant context resolution.

Bridges the Next.js portal (cardinal-portal) with the Railway FastAPI engine.
The portal sends Clerk-issued JWTs in the Authorization header; this module
validates them against Clerk's published JWKS and extracts:

- ``sub``       -- Clerk user ID
- ``org_id``    -- Clerk Organization ID
- ``org_slug``  -- canonical CE tenant slug (used by ce-graph)
- ``org_role``  -- admin / member
- ``tier``      -- 1 / 2 / 3 (from Organization.public_metadata.tier)

Set ``CLERK_JWKS_URL`` and (optionally) ``CLERK_AUDIENCE`` in env. If unset,
all auth-required endpoints fail closed with 503 (server misconfigured).
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Malformed token: {exc}")

    kid = unverified_header.get("kid")
    key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Signing key not found in JWKS")

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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {exc}")


@lru_cache(maxsize=1)
def _config() -> tuple[str | None, str | None]:
    return os.environ.get("CLERK_JWKS_URL"), os.environ.get("CLERK_AUDIENCE")


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("Authorization") or ""
    if not header.lower().startswith("bearer "):
        return None
    return header.split(" ", 1)[1].strip() or None


async def get_auth(request: Request) -> ClerkAuthContext:
    """FastAPI dependency: validate Clerk JWT, return context. 401 if missing/invalid."""
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

    tier_raw = claims.get("tier")
    tier: int | None
    try:
        tier = int(tier_raw) if tier_raw is not None and str(tier_raw).strip() != "" else None
    except (TypeError, ValueError):
        tier = None

    ctx = ClerkAuthContext(
        user_id=str(claims.get("sub", "")),
        org_id=claims.get("org_id"),
        org_slug=claims.get("org_slug"),
        org_role=claims.get("org_role"),
        tier=tier,
        raw_claims=claims,
    )
    request.state.auth = ctx
    return ctx


async def get_auth_with_org(ctx: ClerkAuthContext = Depends(get_auth)) -> ClerkAuthContext:
    """Same as ``get_auth`` but also requires an active org. Use for tenant-scoped endpoints."""
    ctx.require_org()
    return ctx


# ---------------------------------------------------------------------------
# Backward-compatible tenant resolution
# ---------------------------------------------------------------------------
#
# We can't switch every existing endpoint to required-auth without breaking
# Scott's local CLI/UI workflows on day one. ``resolve_tenant`` is the bridge:
#
#   1. If a valid Clerk JWT is present -> use its ``org_slug``.
#   2. Else if ``CE_DEV_TENANT`` env var is set -> use that.
#   3. Else fall back to ``cardinal-element`` (CE's own reference tenant).
#
# This means today's unauth'd local calls keep writing to/reading from the
# cardinal-element tenant (i.e. they "just work"), while portal-driven calls
# carrying a real JWT get scoped to the customer's tenant.
#
# Production: set CLERK_JWKS_URL + remove CE_DEV_TENANT to lock down. Endpoints
# that should always require auth (admin, billing) use ``get_auth_with_org``
# directly instead of ``resolve_tenant``.

DEFAULT_TENANT = "cardinal-element"


async def resolve_tenant(request: Request) -> str:
    """Best-effort tenant resolution. Returns a slug, never raises.

    Use as a FastAPI dependency on existing endpoints to add tenant scoping
    without breaking unauth'd callers.
    """
    # 1. Try the JWT path. Swallow auth errors -- we're being lenient here.
    if _config()[0]:  # CLERK_JWKS_URL is set
        token = _bearer_token(request)
        if token:
            try:
                ctx = await get_auth(request)
                if ctx.org_slug:
                    return ctx.org_slug
            except HTTPException:
                pass  # fall through to env/default

    # 2. Env override (local dev convenience)
    env_slug = os.environ.get("CE_DEV_TENANT")
    if env_slug:
        return env_slug

    # 3. Default to CE's own tenant
    return DEFAULT_TENANT


__all__ = [
    "ClerkAuthContext",
    "DEFAULT_TENANT",
    "get_auth",
    "get_auth_with_org",
    "resolve_tenant",
]
