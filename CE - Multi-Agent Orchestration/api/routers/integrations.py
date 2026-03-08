"""Integration endpoints for Tools & MCP Hub."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from api.database import get_session
from api.models import Integration
from api.tool_registry import MCP_SERVER_CATALOG, TOOL_CATALOG

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


# ── Seed data ────────────────────────────────────────────────────────────────

DOMAIN_DESCRIPTIONS = {
    "sec_edgar": "SEC EDGAR company filings and financials",
    "github": "GitHub org analysis and tech stack profiling",
    "census": "Census Bureau market size and industry benchmarks",
    "bls": "Bureau of Labor Statistics employment data",
    "pricing": "CE engagement pricing models",
    "pinecone": "Vector knowledge base search",
    "image_gen": "AI image generation (DALL-E, Gemini)",
    "web": "Web search and content fetching",
    "notion": "Notion workspace integration",
    "output": "Document output and PDF export",
    "qa": "Quality assurance validation",
}


def _seed_integrations(session: Session) -> None:
    """Seed integrations table from TOOL_CATALOG and MCP_SERVER_CATALOG."""
    # Tool domains
    domains: dict[str, int] = {}
    for tool in TOOL_CATALOG.values():
        domain = tool["domain"]
        domains[domain] = domains.get(domain, 0) + 1

    for domain, count in domains.items():
        session.add(Integration(
            name=domain,
            type="tool_domain",
            enabled=False,
            config_json=json.dumps({"tool_count": count}),
            description=DOMAIN_DESCRIPTIONS.get(domain, ""),
            is_builtin=True,
        ))

    # MCP servers
    for key, server in MCP_SERVER_CATALOG.items():
        session.add(Integration(
            name=key,
            type="mcp_server",
            enabled=False,
            config_json=json.dumps({"transport": server.get("transport", "stdio")}),
            description=server.get("description", ""),
            is_builtin=True,
        ))

    session.commit()


# ── Request models ───────────────────────────────────────────────────────────

class IntegrationUpdate(BaseModel):
    enabled: bool | None = None
    config_json: str | None = None


class McpServerCreate(BaseModel):
    name: str
    description: str = ""
    url: str = ""
    transport: str = "stdio"


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("")
def list_integrations(session: Session = Depends(get_session)) -> list[dict]:
    # Seed on first call if table is empty
    count = session.exec(select(Integration)).first()
    if count is None:
        _seed_integrations(session)

    rows = session.exec(select(Integration)).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "type": r.type,
            "enabled": r.enabled,
            "config": json.loads(r.config_json),
            "api_key_configured": r.api_key_configured,
            "description": r.description,
            "is_builtin": r.is_builtin,
        }
        for r in rows
    ]


@router.put("/{name}")
def update_integration(
    name: str, body: IntegrationUpdate, session: Session = Depends(get_session)
) -> dict:
    row = session.exec(select(Integration).where(Integration.name == name)).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Integration '{name}' not found")

    if body.enabled is not None:
        row.enabled = body.enabled
    if body.config_json is not None:
        row.config_json = body.config_json

    session.add(row)
    session.commit()
    session.refresh(row)
    return {
        "id": row.id,
        "name": row.name,
        "type": row.type,
        "enabled": row.enabled,
        "config": json.loads(row.config_json),
        "api_key_configured": row.api_key_configured,
        "description": row.description,
        "is_builtin": row.is_builtin,
    }


@router.post("", status_code=201)
def create_integration(
    body: McpServerCreate, session: Session = Depends(get_session)
) -> dict:
    existing = session.exec(
        select(Integration).where(Integration.name == body.name)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Integration '{body.name}' already exists")

    row = Integration(
        name=body.name,
        type="mcp_server",
        enabled=False,
        config_json=json.dumps({"transport": body.transport, "url": body.url}),
        description=body.description,
        is_builtin=False,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return {
        "id": row.id,
        "name": row.name,
        "type": row.type,
        "enabled": row.enabled,
        "config": json.loads(row.config_json),
        "api_key_configured": row.api_key_configured,
        "description": row.description,
        "is_builtin": row.is_builtin,
    }


@router.delete("/{name}", status_code=204)
def delete_integration(name: str, session: Session = Depends(get_session)) -> None:
    row = session.exec(select(Integration).where(Integration.name == name)).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Integration '{name}' not found")
    if row.is_builtin:
        raise HTTPException(status_code=400, detail="Cannot delete builtin integrations")
    session.delete(row)
    session.commit()
