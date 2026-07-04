"""Auth introspection endpoint.

The portal calls ``GET /api/auth/me`` to verify the auth bridge is working
and to read the active session's tenant + tier context.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.middleware.clerk_auth import ClerkAuthContext, get_auth

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me")
async def get_me(ctx: ClerkAuthContext = Depends(get_auth)) -> dict:
    """Return the resolved Clerk session claims. Used to validate the auth bridge."""
    return {
        "sub": ctx.user_id,
        "org_id": ctx.org_id,
        "org_slug": ctx.org_slug,
        "org_role": ctx.org_role,
        "tier": ctx.tier,
        "plan": ctx.plan,
        "features": sorted(ctx.features),
    }


@router.get("/health")
async def auth_health() -> dict:
    """Unauthenticated endpoint to confirm the auth router is mounted."""
    import os

    return {
        "ok": True,
        "clerk_configured": bool(os.environ.get("CLERK_JWKS_URL")),
    }
