"""Base class for decentralized protocol orchestrators (P53-P57).

A TickOrchestrator is a pure scheduler. It advances ticks, collects agent actions
in parallel, writes them to the Blackboard verbatim, and checks termination predicates.
It does NOT synthesize content, filter contributions by judgment, or decide winners.

All content-based decisions happen inside agent.chat() calls. All aggregation happens
in deterministic helpers in protocols.decentralized_actions.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import anthropic

from protocols.blackboard import Blackboard
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from protocols.decentralized_actions import agent_name
from protocols.llm import agent_complete, filter_exceptions_aligned


@dataclass
class TickResult:
    """One tick of a tick-scheduled protocol."""

    tick: int
    entries_written: int
    agents_acted: list[str]
    agents_halted: list[str]
    elapsed_seconds: float = 0.0


class TickOrchestrator:
    """Pure tick scheduler for decentralized protocols.

    Subclasses implement:
      - protocol_key: class attribute, used for Blackboard protocol_id and smoke-test paths
      - decentralization_manifest(): returns the four-dimension scorecard
      - render_prompt_for(agent, tick): returns the prompt text based on current BB state
      - handle_response(agent, text, tick): parses + writes to BB, returns True if agent halted
      - should_terminate(tick): returns True when distributed termination predicate fires

    Subclasses also define their own `run(question, ...)` that drives tick() until termination
    and builds the final result from deterministic aggregation of BB entries.
    """

    protocol_key: str = "tick_base"
    max_ticks: int = 10
    smoke_tests_dir: str = "smoke-tests"

    def __init__(
        self,
        agents: list[Any],
        *,
        thinking_model: str | None = None,
        orchestration_model: str | None = None,
    ) -> None:
        self.agents = agents
        self.thinking_model = thinking_model or THINKING_MODEL
        self.orchestration_model = orchestration_model or ORCHESTRATION_MODEL
        self.client = anthropic.AsyncAnthropic()
        self.blackboard = Blackboard(protocol_id=self.protocol_key)
        self._halted_agents: set[str] = set()
        self._start_time = time.time()

    # ------------------------------------------------------------------
    # Lifecycle — subclasses call these
    # ------------------------------------------------------------------

    def write_manifest(self) -> None:
        """Write the four-dimension decentralization scorecard to the Blackboard.

        Called once at the start of run() so inspection tools can confirm
        the protocol's honest claims about each dimension.
        """
        self.blackboard.write(
            topic="decentralization_manifest",
            content=self.decentralization_manifest(),
            author="system",
            stage="init",
            metadata={"protocol_key": self.protocol_key},
        )

    def decentralization_manifest(self) -> dict[str, str]:
        """Override in subclass. Returns {control, information, communication, termination}."""
        raise NotImplementedError

    async def tick_collect(
        self,
        agents_to_query: list[Any],
        stage_label: str,
        tick: int,
        max_tokens: int = 2048,
    ) -> list[tuple[Any, str | None]]:
        """Render prompt per agent and gather responses in parallel.

        Malformed JSON is the subclass's problem to detect — this method just returns
        (agent, text_or_none) tuples. Failures become (agent, None).
        """

        async def _one(agent: Any) -> str:
            prompt = self.render_prompt_for(agent, tick)
            agent_dict = agent if isinstance(agent, dict) else None
            if agent_dict is None and hasattr(agent, "chat"):
                user_msg = prompt
                return await agent.chat(user_msg)
            return await agent_complete(
                agent=agent,
                fallback_model=self.thinking_model,
                messages=[{"role": "user", "content": prompt}],
                thinking_budget=0,
                max_tokens=max_tokens,
                anthropic_client=self.client,
            )

        tasks = [_one(a) for a in agents_to_query]
        raw = await asyncio.gather(*tasks, return_exceptions=True)
        labels = [agent_name(a) for a in agents_to_query]
        aligned = filter_exceptions_aligned(raw, label=f"{self.protocol_key}:{stage_label}", labels=labels)
        return list(zip(agents_to_query, aligned))

    def render_prompt_for(self, agent: Any, tick: int) -> str:
        """Override in subclass. Pure function of (agent, tick, current blackboard state)."""
        raise NotImplementedError

    def mark_halted(self, agent: Any) -> None:
        self._halted_agents.add(agent_name(agent))

    def active_agents(self) -> list[Any]:
        return [a for a in self.agents if agent_name(a) not in self._halted_agents]

    def all_halted(self) -> bool:
        return all(agent_name(a) in self._halted_agents for a in self.agents)

    def dump_audit_log(self, run_id: str) -> Path:
        """Write the Blackboard's full event log to smoke-tests/<protocol>_<run_id>.jsonl."""
        path = Path(self.smoke_tests_dir) / f"{self.protocol_key}_{run_id}.jsonl"
        self.blackboard.to_jsonl(path)
        return path

    def resource_summary(self) -> dict:
        return self.blackboard.resource_signals()
