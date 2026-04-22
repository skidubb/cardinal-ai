"""Dual-mode agent provider — research (lightweight dicts) or production (ServerAgent).

Research mode: Agents are plain dicts with name + system_prompt. Requires explicit opt-in via
    set_agent_mode("research") or AGENT_MODE=research env var.
Production mode: Default. Agents are ServerAgent instances with direct Anthropic API calls,
    native tool-use, Pinecone memory, and DuckDB learning. No subprocess spawning.

Usage:
    from protocols.agent_provider import set_agent_mode, get_agent_mode

    # Production is the default — no configuration needed
    agents = build_production_agents(["ceo", "cfo"])

    # Research mode requires explicit opt-in
    set_agent_mode("research")  # or set AGENT_MODE=research env var
"""

from __future__ import annotations

import logging

from protocols.server_agent import ServerAgent

logger = logging.getLogger(__name__)

_agent_mode: str = "production"


def set_agent_mode(mode: str) -> None:
    """Set the global agent mode ('research' or 'production')."""
    global _agent_mode
    if mode not in ("research", "production"):
        raise ValueError(f"Invalid agent mode: {mode}. Must be 'research' or 'production'.")
    _agent_mode = mode


def get_agent_mode() -> str:
    """Get the current agent mode."""
    return _agent_mode


def _load_db_overrides(keys: list[str]) -> dict[str, dict]:
    """Load per-agent model/temperature overrides from the Agent table.

    Returns a dict keyed by agent key containing only fields that are set
    (non-empty model, explicit temperature). Missing keys or DB unavailability
    resolve to an empty dict so callers fall back to defaults.
    """
    try:
        from sqlmodel import Session, select
        from api.database import engine
        from api.models import Agent as AgentModel
    except Exception:
        return {}

    overrides: dict[str, dict] = {}
    try:
        with Session(engine) as session:
            stmt = select(AgentModel).where(AgentModel.key.in_(keys))  # type: ignore[attr-defined]
            rows = list(session.execute(stmt).scalars())
            for row in rows:
                entry: dict = {}
                if row.model:
                    entry["model"] = row.model
                entry["temperature"] = row.temperature
                overrides[row.key] = entry
    except Exception as exc:
        logger.debug("DB agent override lookup failed: %s", exc, exc_info=True)
    return overrides


def build_production_agents(keys: list[str], model: str = "claude-opus-4-7") -> list[ServerAgent]:
    """Build production agents using ServerAgent (direct Anthropic API + tools).

    Each agent gets:
    - Rich system prompt from Agent Builder (70+ roles)
    - Per-role tool schemas with full agentic tool loop
    - Pinecone memory, DuckDB experience logs (graceful degradation)
    - Real token-level cost tracking from API responses
    - DB-level overrides for model and temperature (when present)

    No subprocess spawning — works in Docker, Railway, any server environment.
    """
    keys_lower = [k.lower() for k in keys]
    overrides = _load_db_overrides(keys_lower)

    agents: list[ServerAgent] = []

    for key_lower in keys_lower:
        ov = overrides.get(key_lower, {})
        agent_model = ov.get("model") or model
        agent_temp = ov.get("temperature")
        agent = ServerAgent(role=key_lower, model=agent_model, temperature=agent_temp)
        agents.append(agent)
        logger.info(
            "Production agent created: %s (%s) model=%s temperature=%s",
            key_lower, agent.name, agent_model, agent_temp,
        )

    return agents
