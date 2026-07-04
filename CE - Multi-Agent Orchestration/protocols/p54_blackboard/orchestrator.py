"""P54: Blackboard (Pandemonium) — Self-dispatched peer contribution.

Reference implementation for the four-dimension decentralization bar.

Flow:
  Tick 0: orchestrator writes the question to the Blackboard.
  Tick N (repeat):
    - Orchestrator renders the current Blackboard snapshot (all entries,
      optionally role-scoped) into each active agent's prompt.
    - Each agent returns either:
        * {"action":"contribute","topic":...,"content":...,"relevance":...}
        * {"action":"halt","reason":...}
    - Orchestrator writes contributions verbatim. Agents that emit halt are
      marked halted for this round.
    - Distributed termination: all agents halted. Safety ceilings: max_ticks
      and max_entries.
  Final: deterministic assembly of all contributions, grouped by topic.

No synthesis. No filtering. No LLM judgment at the orchestrator level.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from ce_shared.env import find_and_load_dotenv

find_and_load_dotenv()  # Must run before langfuse_tracing import so LANGFUSE_SECRET_KEY is visible.

from protocols.blackboard import BlackboardEntry
from protocols.decentralized_actions import (
    Contribution,
    Halt,
    MalformedAction,
    agent_name,
    parse_contribution_or_halt,
)
from protocols.langfuse_tracing import create_span, end_span, trace_protocol
from protocols.llm import agent_complete
from protocols.tick_scheduler import TickOrchestrator

from .prompts import TICK_PROMPT


@dataclass
class BlackboardResult:
    question: str
    contributions: list[dict[str, Any]]
    halts: list[dict[str, str]]
    final_report: str
    ticks_run: int
    termination_reason: str  # "all_halted" | "max_ticks" | "max_entries"
    malformed_actions: list[dict[str, str]]
    decentralization_manifest: dict[str, str]
    resources: dict[str, Any]
    timings: dict[str, float] = field(default_factory=dict)
    run_id: str = ""


class BlackboardProtocolOrchestrator(TickOrchestrator):
    protocol_key = "p54_blackboard"

    def __init__(
        self,
        agents: list[Any],
        *,
        thinking_model: str | None = None,
        orchestration_model: str | None = None,
        max_ticks: int = 6,
        max_entries: int = 120,
    ) -> None:
        super().__init__(
            agents,
            thinking_model=thinking_model,
            orchestration_model=orchestration_model,
        )
        self.max_ticks = max_ticks
        self.max_entries = max_entries

    def decentralization_manifest(self) -> dict[str, str]:
        return {
            "control": "decentralized — each agent decides each tick whether to contribute or halt",
            "information": "decentralized — full Blackboard snapshot shared with every agent each tick",
            "communication": "decentralized — agents exchange via Blackboard entries, peer-readable",
            "termination": "distributed — protocol ends when all agents emit halt (safety ceilings on ticks and entry count)",
        }

    def render_prompt_for(self, agent: Any, tick: int) -> str:
        raise NotImplementedError("P54 renders prompts inline in run()")

    @trace_protocol("p54_blackboard")
    async def run(self, question: str) -> BlackboardResult:
        timings: dict[str, float] = {}
        run_id = uuid.uuid4().hex[:10]
        self.write_manifest()
        self.blackboard.write(
            topic="question", content=question, author="system", stage="init"
        )

        malformed_total: list[MalformedAction] = []
        contributions: list[Contribution] = []
        halts_this_protocol: list[Halt] = []
        termination_reason = "max_ticks"

        for tick in range(1, self.max_ticks + 1):
            # Reset halts at each tick — agents may re-engage if state changed.
            self._halted_agents.clear()

            span = create_span(f"tick:{tick}", {})
            try:
                t0 = time.time()
                active = list(self.agents)
                results, malformed = await self._run_tick(
                    question, active, tick
                )
                for agent, action in results:
                    aname = agent_name(agent)
                    if isinstance(action, Contribution):
                        contributions.append(action)
                        self.blackboard.write(
                            topic=f"contribution:{action.topic}",
                            content={
                                "agent": aname,
                                "topic": action.topic,
                                "content": action.content,
                                "relevance": action.relevance,
                                "tick": tick,
                            },
                            author=aname,
                            stage=f"tick_{tick}",
                            metadata={"relevance": action.relevance, "tick": tick},
                        )
                    elif isinstance(action, Halt):
                        halts_this_protocol.append(action)
                        self.mark_halted(agent)
                        self.blackboard.write(
                            topic="halt",
                            content={"agent": aname, "reason": action.reason, "tick": tick},
                            author=aname,
                            stage=f"tick_{tick}",
                        )

                malformed_total.extend(malformed)
                for m in malformed:
                    self.blackboard.write(
                        topic="malformed_actions",
                        content={"agent": m.agent, "error": m.error, "raw": m.raw},
                        author=m.agent,
                        stage=f"tick_{tick}",
                    )
                    dead = next(
                        (a for a in self.agents if agent_name(a) == m.agent), None
                    )
                    if dead is not None:
                        self.mark_halted(dead)
                        halts_this_protocol.append(
                            Halt(agent=m.agent, reason=f"malformed: {m.error}")
                        )

                timings[f"tick_{tick}"] = time.time() - t0
                end_span(
                    span,
                    output=(
                        f"{len([r for r in results if isinstance(r[1], Contribution)])} "
                        f"contrib, {len([r for r in results if isinstance(r[1], Halt)])} halt"
                    ),
                )
            except Exception:
                end_span(span, error=f"tick {tick} failed")
                raise

            if self.all_halted():
                termination_reason = "all_halted"
                break
            if len(self.blackboard._entries) >= self.max_entries:
                termination_reason = "max_entries"
                break

        final_report = self._assemble(contributions)
        self.blackboard.write(
            topic="final_report",
            content=final_report,
            author="system",
            stage="assemble",
        )
        self.dump_audit_log(run_id)

        return BlackboardResult(
            question=question,
            contributions=[
                {
                    "agent": c.agent,
                    "topic": c.topic,
                    "content": c.content,
                    "relevance": c.relevance,
                }
                for c in contributions
            ],
            halts=[{"agent": h.agent, "reason": h.reason} for h in halts_this_protocol],
            final_report=final_report,
            ticks_run=min(self.max_ticks, len(timings)),
            termination_reason=termination_reason,
            malformed_actions=[
                {"agent": m.agent, "error": m.error, "raw": m.raw}
                for m in malformed_total
            ],
            decentralization_manifest=self.decentralization_manifest(),
            resources=self.blackboard.resource_signals(),
            timings=timings,
            run_id=run_id,
        )

    # ------------------------------------------------------------------

    async def _run_tick(
        self, question: str, active_agents: list[Any], tick: int
    ) -> tuple[list[tuple[Any, Any]], list[MalformedAction]]:
        snapshot = self._render_snapshot()
        active_names = ", ".join(agent_name(a) for a in active_agents)

        async def _one(agent: Any) -> tuple[Any, str]:
            prompt = TICK_PROMPT.format(
                agent_name=agent_name(agent),
                system_prompt=self._system_prompt(agent),
                question=question,
                tick=tick,
                max_ticks=self.max_ticks,
                blackboard_snapshot=snapshot,
                active_agents=active_names,
            )
            if hasattr(agent, "chat") and callable(agent.chat):
                text = await agent.chat(prompt)
            else:
                text = await agent_complete(
                    agent=agent,
                    fallback_model=self.thinking_model,
                    messages=[{"role": "user", "content": prompt}],
                    thinking_budget=0,
                    max_tokens=2048,
                    anthropic_client=self.client,
                )
            return agent, text

        raw = await asyncio.gather(
            *[_one(a) for a in active_agents], return_exceptions=True
        )

        results: list[tuple[Any, Any]] = []
        malformed: list[MalformedAction] = []
        for item in raw:
            if isinstance(item, BaseException):
                continue
            agent, text = item
            aname = agent_name(agent)
            parsed = parse_contribution_or_halt(aname, text)
            if isinstance(parsed, (Contribution, Halt)):
                results.append((agent, parsed))
            else:
                malformed.append(parsed)
        return results, malformed

    def _render_snapshot(self) -> str:
        """Render the Blackboard as a readable snapshot for agent prompts."""
        entries = [e for e in self.blackboard._entries if e.topic != "decentralization_manifest"]
        if not entries:
            return "(empty — no entries yet)"

        by_topic: dict[str, list[BlackboardEntry]] = defaultdict(list)
        for e in entries:
            by_topic[e.topic].append(e)

        lines: list[str] = []
        for topic in sorted(by_topic.keys()):
            lines.append(f"### {topic}")
            for e in by_topic[topic]:
                content = e.content
                if isinstance(content, dict):
                    # Try to extract the interesting bits
                    agent = content.get("agent", e.author)
                    body = content.get("content") or content.get("reason") or str(
                        {k: v for k, v in content.items() if k not in ("agent", "tick")}
                    )
                    lines.append(f"  - [{agent}] {body}")
                else:
                    lines.append(f"  - [{e.author}] {content}")
            lines.append("")
        return "\n".join(lines).strip()

    def _assemble(self, contributions: list[Contribution]) -> str:
        """Deterministic markdown: group by topic, order by (topic, tick/time)."""
        if not contributions:
            return "(no contributions)"

        by_topic: dict[str, list[Contribution]] = defaultdict(list)
        for c in contributions:
            by_topic[c.topic].append(c)

        lines: list[str] = []
        for topic in sorted(by_topic.keys()):
            lines.append(f"## {topic.replace('_', ' ').title()}")
            for c in by_topic[topic]:
                lines.append(f"**{c.agent}** (relevance={c.relevance:.2f})")
                lines.append("")
                lines.append(c.content.strip())
                lines.append("")
        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def _system_prompt(agent: Any) -> str:
        if isinstance(agent, dict):
            return agent.get("system_prompt", "")
        return getattr(agent, "system_prompt", "") or ""
