"""Memory brief preview -- "what the graph knows" before a run.

Customers see this light up on the /run page as they type their question:

    > 2 corrections apply to Acme Corp.
    > 3 prior decisions in SaaS vertical.
    > 1 lesson from past expansion engagements.

It's the single most visceral "my system is learning" surface. Every time a
customer sees the brief grow, the product demonstrates compounding value.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.middleware.clerk_auth import resolve_tenant

router = APIRouter(prefix="/api/context", tags=["context"])


class PreviewRequest(BaseModel):
    question: str


@router.post("/preview")
async def preview(
    payload: PreviewRequest,
    tenant_slug: str = Depends(resolve_tenant),
) -> dict:
    """Return the structured context brief that would be injected for this question."""
    from protocols.context_assembler import assemble_context_preview
    return await assemble_context_preview(tenant_slug, payload.question)
