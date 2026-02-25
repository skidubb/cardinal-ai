"""Dumb orchestrator — pure state machine over a blackboard.

while True: watch → match → dispatch.
Orchestrator never reads content. Only checks triggers and dispatches stages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from protocols.blackboard import Blackboard
@dataclass
class Stage:
    name: str
    trigger: Callable[[Blackboard], bool]
    execute: Callable  # async (bb, agents, **config) -> None
    agents_filter: str | None = None  # "@red", "@blue", agent names, or None=all


@dataclass
class ProtocolDef:
    protocol_id: str
    stages: list[Stage]
    scoping_rules: dict | None = None


class Orchestrator:
    """Fires stages when their triggers match. Never reads entry content."""

    async def run(
        self,
        protocol: ProtocolDef,
        question: str,
        agents: list[dict],
        **config,
    ) -> Blackboard:
        bb = Blackboard(protocol.protocol_id, protocol.scoping_rules)
        bb.write("question", question, author="system", stage="init")

        pending = list(protocol.stages)
        while pending:
            fired = []
            for stage in pending:
                if stage.trigger(bb):
                    stage_agents = _filter_agents(agents, stage.agents_filter)
                    await stage.execute(bb, stage_agents, **config)
                    fired.append(stage)
            for s in fired:
                pending.remove(s)
            if not fired:
                break  # done or deadlocked

        return bb


def _filter_agents(agents: list[dict], filter_spec: str | None) -> list[dict]:
    """Filter agents by spec: '@category', comma-separated names, or None=all."""
    if filter_spec is None:
        return agents
    if filter_spec.startswith("@"):
        category = filter_spec[1:]
        return [a for a in agents if category in a.get("categories", [])]
    names = {n.strip() for n in filter_spec.split(",")}
    return [a for a in agents if a["name"] in names]
