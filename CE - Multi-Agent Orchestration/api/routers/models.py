"""Model catalog endpoint — read-only, no auth/tenant scoping needed."""

from __future__ import annotations

from fastapi import APIRouter

from protocols.config import BALANCED_MODEL, ORCHESTRATION_MODEL, THINKING_MODEL
from protocols.model_catalog import TIERS, catalog_dump

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("")
def list_models() -> dict:
    return {
        "models": catalog_dump(),
        "defaults": {
            "thinking": THINKING_MODEL,
            "orchestration": ORCHESTRATION_MODEL,
            "balanced": BALANCED_MODEL,
        },
        "tiers": TIERS,
    }
