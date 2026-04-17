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


def build_production_agents(keys: list[str], model: str = "claude-opus-4-7") -> list[ServerAgent]:
    """Build production agents using ServerAgent (direct Anthropic API + tools).

    Each agent gets:
    - Rich system prompt from Agent Builder (70+ roles)
    - Per-role tool schemas with full agentic tool loop
    - Pinecone memory, DuckDB experience logs (graceful degradation)
    - Real token-level cost tracking from API responses

    No subprocess spawning — works in Docker, Railway, any server environment.
    """
    agents: list[ServerAgent] = []

    for key in keys:
        key_lower = key.lower()
        agent = ServerAgent(role=key_lower, model=model)
        agents.append(agent)
        logger.info("Production agent created: %s (%s)", key_lower, agent.name)

    return agents
