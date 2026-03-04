"""Dual-mode agent provider — research (lightweight dicts) or production (real SDK agents).

Research mode: Current behavior. Agents are plain dicts with name + system_prompt.
Production mode: Agents are AgentBridge wrappers around SdkAgent from Agent Builder.
    These have real tools, Pinecone memory, and DuckDB learning.

Usage:
    from protocols.agent_provider import set_agent_mode, get_agent_mode

    set_agent_mode("production")  # Switch to real agents
    agents = build_agents(["ceo", "cfo"], mode=get_agent_mode())
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_agent_mode: str = "research"


def set_agent_mode(mode: str) -> None:
    """Set the global agent mode ('research' or 'production')."""
    global _agent_mode
    if mode not in ("research", "production"):
        raise ValueError(f"Invalid agent mode: {mode}. Must be 'research' or 'production'.")
    _agent_mode = mode


def get_agent_mode() -> str:
    """Get the current agent mode."""
    return _agent_mode


class AgentBridge:
    """Wraps an Agent Builder SdkAgent to be dict-compatible for protocols.

    Protocols access agents via agent["name"] and agent["system_prompt"].
    This bridge supports both dict-style access and the chat() method
    that llm.py's agent_complete() detects for production routing.
    """

    def __init__(self, sdk_agent, role: str, system_prompt: str):
        self._sdk = sdk_agent
        self.name = sdk_agent.config.name
        self.system_prompt = system_prompt
        self.role = role

    def __getitem__(self, key: str):
        """Dict-style access for protocol compatibility."""
        if key == "name":
            return self.name
        if key == "system_prompt":
            return self.system_prompt
        raise KeyError(key)

    def get(self, key: str, default=None):
        """Dict-style .get() for protocol compatibility."""
        try:
            return self[key]
        except KeyError:
            return default

    @property
    def tool_calls(self) -> list[dict]:
        """Tool calls from the last chat() invocation."""
        return getattr(self._sdk, "tool_calls", [])

    async def chat(self, message: str) -> str:
        """Forward to the real SdkAgent with tools, memory, and learning."""
        return await self._sdk.chat(message)


def build_production_agents(keys: list[str]) -> list[AgentBridge]:
    """Build production agents from Agent Builder's SdkAgent.

    Adds Agent Builder's src/ to sys.path if needed, then creates
    SdkAgent instances wrapped in AgentBridge for protocol compatibility.
    """
    # Ensure Agent Builder is importable
    agent_builder_src = Path(__file__).resolve().parents[1] / ".." / "CE - Agent Builder" / "src"
    agent_builder_src = agent_builder_src.resolve()
    if str(agent_builder_src) not in sys.path:
        sys.path.insert(0, str(agent_builder_src))

    try:
        from csuite.agents.sdk_agent import SdkAgent
    except ImportError as e:
        logger.error(
            "Cannot import Agent Builder SdkAgent. "
            "Ensure 'CE - Agent Builder' is installed or adjacent. Error: %s", e
        )
        raise RuntimeError(
            "Production mode requires Agent Builder. "
            "Install with: cd 'CE - Agent Builder' && pip install -e '.[sdk]'"
        ) from e

    # Import orchestration's own agent registry for system prompts
    from protocols.agents import BUILTIN_AGENTS

    agents: list[AgentBridge] = []
    for key in keys:
        key_lower = key.lower()
        if key_lower not in BUILTIN_AGENTS:
            logger.warning("Unknown agent '%s' — skipping production build", key)
            continue

        builtin = BUILTIN_AGENTS[key_lower]
        system_prompt = builtin.get("system_prompt", "")

        try:
            sdk_agent = SdkAgent(role=key_lower)
            bridge = AgentBridge(sdk_agent, role=key_lower, system_prompt=system_prompt)
            agents.append(bridge)
            logger.info("Production agent created: %s (%s)", key_lower, sdk_agent.config.name)
        except (ValueError, KeyError) as e:
            logger.warning(
                "Failed to create production agent '%s': %s. "
                "Falling back to research mode for this agent.", key, e
            )
            # Return the dict directly — protocols handle dicts natively
            agents.append(builtin)  # type: ignore[arg-type]

    return agents
