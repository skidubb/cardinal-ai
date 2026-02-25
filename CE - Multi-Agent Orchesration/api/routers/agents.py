"""Agent endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from api.database import get_session
from api.models import Agent
from api.tool_registry import (
    MCP_SERVER_CATALOG,
    ROLE_KB_NAMESPACES,
    ROLE_MCP_MAP,
    ROLE_TOOL_MAP,
    TOOL_CATALOG,
)
from protocols.agents import AGENT_CATEGORIES, BUILTIN_AGENTS

router = APIRouter(prefix="/api/agents", tags=["agents"])
tools_router = APIRouter(prefix="/api", tags=["tools"])


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_parent_executive(category: str) -> str:
    """Map a sub-agent category to its parent executive role."""
    mapping = {
        "executive": "",
        "ceo-team": "ceo",
        "cfo-team": "cfo",
        "cmo-team": "cmo",
        "coo-team": "coo",
        "cpo-team": "cpo",
        "cto-team": "cto",
        "gtm-leadership": "cro",
        "gtm-sales": "cro",
        "gtm-marketing": "cmo",
        "gtm-partners": "cro",
        "gtm-success": "cro",
        "gtm-ops": "cro",
        "external": "",
    }
    return mapping.get(category, "")


def _builtin_to_dict(key: str, data: dict) -> dict:
    """Convert a BUILTIN_AGENTS entry to API response format."""
    category = ""
    for cat, keys in AGENT_CATEGORIES.items():
        if key in keys:
            category = cat
            break

    role = key if category == "executive" else _get_parent_executive(category)

    return {
        "key": key,
        "name": data.get("name", key),
        "category": category,
        "model": data.get("model", ""),
        "temperature": 1.0,
        "max_tokens": 8192,
        "system_prompt": data.get("system_prompt", ""),
        "context_scope": data.get("context_scope", []),
        "is_builtin": True,
        "tools": ROLE_TOOL_MAP.get(role, []),
        "mcp_servers": ROLE_MCP_MAP.get(role, []),
        "kb_namespaces": ROLE_KB_NAMESPACES.get(role, []),
        "kb_write_enabled": False,
        "deliverable_template": "",
        "frameworks": [],
        "delegation": [],
        "constraints": [],
        "personality": "",
        "communication_style": "",
    }


def _db_agent_to_dict(a: Agent) -> dict:
    """Convert a DB Agent record to API response format."""
    return {
        "key": a.key,
        "name": a.name,
        "category": a.category,
        "model": a.model,
        "temperature": a.temperature,
        "max_tokens": a.max_tokens,
        "system_prompt": a.system_prompt,
        "context_scope": [],
        "is_builtin": a.is_builtin,
        "tools": json.loads(a.tools_json),
        "mcp_servers": json.loads(a.mcp_servers_json),
        "kb_namespaces": json.loads(a.kb_namespaces_json),
        "kb_write_enabled": a.kb_write_enabled,
        "deliverable_template": a.deliverable_template,
        "frameworks": json.loads(a.frameworks_json),
        "delegation": json.loads(a.delegation_json),
        "constraints": json.loads(a.constraints_json),
        "personality": a.personality,
        "communication_style": a.communication_style,
    }


# ── Tools endpoint (separate router to avoid /{key} conflict) ────────────────

@tools_router.get("/tools")
def list_tools():
    return {"tools": TOOL_CATALOG, "mcp_servers": MCP_SERVER_CATALOG}


# ── Agent endpoints ──────────────────────────────────────────────────────────

@router.get("")
def list_agents(session: Session = Depends(get_session)) -> list[dict]:
    # Load DB agents (rich overrides) keyed by agent key
    db_agents = {a.key: a for a in session.exec(select(Agent)).all()}

    agents = []
    for k, v in BUILTIN_AGENTS.items():
        if k in db_agents:
            agents.append(_db_agent_to_dict(db_agents[k]))
        else:
            agents.append(_builtin_to_dict(k, v))

    # Custom (non-builtin) agents from DB
    for key, a in db_agents.items():
        if key not in BUILTIN_AGENTS:
            agents.append(_db_agent_to_dict(a))

    return agents


@router.post("", status_code=201)
def create_agent(agent: Agent, session: Session = Depends(get_session)) -> Agent:
    if agent.key in BUILTIN_AGENTS:
        raise HTTPException(status_code=409, detail=f"Agent key '{agent.key}' is a builtin agent")
    found = session.exec(select(Agent).where(Agent.key == agent.key)).first()
    if found:
        raise HTTPException(status_code=409, detail=f"Agent key '{agent.key}' already exists")
    agent.is_builtin = False
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


@router.get("/{key}")
def get_agent(key: str, session: Session = Depends(get_session)) -> dict:
    db_agent = session.exec(select(Agent).where(Agent.key == key)).first()
    if db_agent:
        return _db_agent_to_dict(db_agent)

    if key in BUILTIN_AGENTS:
        return _builtin_to_dict(key, BUILTIN_AGENTS[key])

    raise HTTPException(status_code=404, detail=f"Agent '{key}' not found")


@router.put("/{key}")
def update_agent(key: str, body: dict, session: Session = Depends(get_session)) -> dict:
    agent = session.exec(select(Agent).where(Agent.key == key)).first()
    if not agent:
        if key not in BUILTIN_AGENTS:
            raise HTTPException(status_code=404, detail=f"Agent '{key}' not found")
        agent = Agent(key=key, name=BUILTIN_AGENTS[key]["name"], is_builtin=True)

    for field in ["name", "category", "model", "temperature", "max_tokens", "system_prompt",
                  "kb_write_enabled", "deliverable_template", "personality", "communication_style"]:
        if field in body:
            setattr(agent, field, body[field])

    for field, json_field in [("tools", "tools_json"), ("mcp_servers", "mcp_servers_json"),
                               ("kb_namespaces", "kb_namespaces_json"), ("frameworks", "frameworks_json"),
                               ("delegation", "delegation_json"), ("constraints", "constraints_json")]:
        if field in body:
            setattr(agent, json_field, json.dumps(body[field]))

    session.add(agent)
    session.commit()
    session.refresh(agent)
    return _db_agent_to_dict(agent)


@router.post("/import-rich")
def import_rich(session: Session = Depends(get_session)):
    from api.import_rich_agents import import_rich_agents
    stats = import_rich_agents()
    return {"status": "ok", **stats}
