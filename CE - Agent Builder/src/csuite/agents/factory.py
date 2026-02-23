"""
Agent factory — creates either legacy BaseAgent or SDK agent based on config.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from csuite.agents import CEOAgent, CFOAgent, CMOAgent, COOAgent, CPOAgent, CROAgent, CTOAgent
from csuite.config import get_settings

if TYPE_CHECKING:
    from csuite.agents.base import BaseAgent
    from csuite.tools.cost_tracker import CostTracker

_LEGACY_CLASSES: dict[str, type[BaseAgent]] = {
    "ceo": CEOAgent,
    "cfo": CFOAgent,
    "cto": CTOAgent,
    "cmo": CMOAgent,
    "coo": COOAgent,
    "cpo": CPOAgent,
    "cro": CROAgent,
}


def create_agent(role: str, cost_tracker: CostTracker | None = None, **kwargs):
    """Create an agent for the given role using the configured backend.

    Returns a BaseAgent (legacy) or SdkAgent depending on AGENT_BACKEND setting.
    Both expose async chat(message) -> str.
    """
    backend = get_settings().agent_backend

    if backend == "sdk":
        from csuite.agents.sdk_agent import SdkAgent
        return SdkAgent(role=role, cost_tracker=cost_tracker)

    agent_class = _LEGACY_CLASSES.get(role)
    if not agent_class:
        raise ValueError(f"Unknown agent role: {role}")
    return agent_class(cost_tracker=cost_tracker, **kwargs)
