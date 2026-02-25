"""Protocol endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from api.manifest import get_protocol_manifest

router = APIRouter(prefix="/api/protocols", tags=["protocols"])


@router.get("")
def list_protocols() -> list[dict]:
    return get_protocol_manifest()
