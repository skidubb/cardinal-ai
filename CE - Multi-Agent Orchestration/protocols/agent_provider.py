"""Dual-mode agent provider — research (lightweight dicts) or production (real SDK agents).

Research mode: Agents are plain dicts with name + system_prompt. Requires explicit opt-in via
    set_agent_mode("research") or AGENT_MODE=research env var.
Production mode: Default. Agents are AgentBridge wrappers around SdkAgent from Agent Builder.
    These have real tools, Pinecone memory, and DuckDB learning.

Usage:
    from protocols.agent_provider import set_agent_mode, get_agent_mode

    # Production is the default — no configuration needed
    agents = build_production_agents(["ceo", "cfo"])

    # Research mode requires explicit opt-in
    set_agent_mode("research")  # or set AGENT_MODE=research env var
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

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


def _resolve_agent_builder_src() -> Path:
    """Resolve the Agent Builder src/ path.

    Checks CE_AGENT_BUILDER_PATH env var first. Falls back to the computed
    sibling directory relative to this file's location.
    """
    env_path = os.environ.get("CE_AGENT_BUILDER_PATH")
    if env_path:
        return Path(env_path).resolve()
    # protocols/agent_provider.py → protocols/ → CE - Multi-Agent Orchestration/ → CE - AGENTS/
    # then sibling CE - Agent Builder/src
    return (Path(__file__).resolve().parents[2] / "CE - Agent Builder" / "src").resolve()


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

    Raises RuntimeError (with all failed agent names listed) if ANY agent
    fails to instantiate. No partial results — all agents must load as SdkAgent.
    """
    # Ensure Agent Builder is importable using env-var-overridable path resolution
    agent_builder_src = _resolve_agent_builder_src()
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
    failed_agents: list[tuple[str, str]] = []

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
        except Exception as e:  # noqa: BLE001
            failed_agents.append((key_lower, str(e)))

    if failed_agents:
        names = ", ".join(k for k, _ in failed_agents)
        details = "; ".join(f"{k}: {e}" for k, e in failed_agents)
        raise RuntimeError(
            f"Failed to instantiate production agents: [{names}]. "
            f"Details: {details}. "
            "All agents must load as SdkAgent — no partial results allowed. "
            "Fix: verify ANTHROPIC_API_KEY is set and Agent Builder is installed."
        )

    return agents
