"""P53: Contract Net Protocol — Decentralized task allocation.

Flow:
  1. Orchestrator mechanically splits the question into sub-tasks (cheap LLM call,
     NOT a content-judgment step — it just parses the question structure).
  2. Tick 1: each agent bids on the sub-tasks they want, in parallel. Bids written
     to Blackboard verbatim.
  3. Mechanical: Hungarian assignment picks winners. Deterministic.
  4. Tick 2: awarded agents execute their assigned task in parallel. Deliverables
     written to Blackboard verbatim.
  5. Mechanical assembly: concatenate deliverables in task-board order.

No synthesis. No LLM "picks the best." No orchestrator judgment.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ce_shared.env import find_and_load_dotenv

find_and_load_dotenv()  # Must run before langfuse_tracing import so LANGFUSE_SECRET_KEY is visible.

from protocols.decentralized_actions import (
    Bid,
    MalformedAction,
    agent_name,
    hungarian_assign,
    parse_bid,
)
from protocols.langfuse_tracing import trace_protocol, create_span, end_span
from protocols.llm import extract_text, llm_complete, parse_json_object
from protocols.tick_scheduler import TickOrchestrator

from .prompts import BID_PROMPT, EXECUTE_PROMPT, TASK_SPLIT_PROMPT


@dataclass
class ContractNetResult:
    question: str
    tasks: list[dict[str, str]]
    bids: list[dict[str, Any]]
    awards: dict[str, str]
    deliverables: dict[str, str]
    final_report: str
    malformed_actions: list[dict[str, str]]
    decentralization_manifest: dict[str, str]
    timings: dict[str, float] = field(default_factory=dict)
    run_id: str = ""


class ContractNetOrchestrator(TickOrchestrator):
    """Pure tick scheduler: announce → bid → Hungarian → execute → concat."""

    protocol_key = "p53_contract_net"
    max_ticks = 3

    def decentralization_manifest(self) -> dict[str, str]:
        return {
            "control": "decentralized — agents self-select tasks via bidding",
            "information": "decentralized — full task board shared on the Blackboard",
            "communication": "decentralized — agents exchange via Blackboard entries",
            "termination": "deterministic quorum — protocol ends when all awarded tasks have deliverables",
        }

    def render_prompt_for(self, agent: Any, tick: int) -> str:
        # Base-class hook; actual rendering happens inline in run() for clarity.
        raise NotImplementedError("P53 renders prompts inline in run()")

    @trace_protocol("p53_contract_net")
    async def run(self, question: str) -> ContractNetResult:
        timings: dict[str, float] = {}
        run_id = uuid.uuid4().hex[:10]
        self.write_manifest()
        self.blackboard.write(
            topic="question",
            content=question,
            author="system",
            stage="init",
        )

        # Stage 1 — Task decomposition (mechanical, parse-only LLM helper, no judgment)
        span = create_span("stage:task_split", {})
        try:
            t0 = time.time()
            tasks = await self._split_tasks(question)
            self.blackboard.write(
                topic="task_board",
                content=tasks,
                author="system",
                stage="task_split",
                metadata={"task_count": len(tasks)},
            )
            timings["stage1_task_split"] = time.time() - t0
            end_span(span, output=f"{len(tasks)} tasks")
        except Exception:
            end_span(span, error="task_split failed")
            raise

        # Stage 2 — Bidding (parallel agent calls)
        span = create_span("stage:bidding", {"agent_count": len(self.agents)})
        try:
            t0 = time.time()
            bids, malformed = await self._collect_bids(question, tasks)
            for b in bids:
                self.blackboard.write(
                    topic="bids",
                    content={
                        "agent": b.agent,
                        "task_id": b.task_id,
                        "fit_score": b.fit_score,
                        "confidence": b.confidence,
                        "cost_estimate": b.cost_estimate,
                        "approach": b.approach,
                    },
                    author=b.agent,
                    stage="bidding",
                )
            for m in malformed:
                self.blackboard.write(
                    topic="malformed_actions",
                    content={"agent": m.agent, "error": m.error, "raw": m.raw},
                    author=m.agent,
                    stage="bidding",
                )
                # Per the plan: malformed = treated as halt for this stage.
                self.mark_halted(next((a for a in self.agents if agent_name(a) == m.agent), None))
            timings["stage2_bidding"] = time.time() - t0
            end_span(span, output=f"{len(bids)} bids, {len(malformed)} malformed")
        except Exception:
            end_span(span, error="bidding failed")
            raise

        # Stage 3 — Mechanical Hungarian assignment
        span = create_span("stage:hungarian_assignment", {})
        try:
            t0 = time.time()
            task_ids = [t["id"] for t in tasks]
            awards = hungarian_assign(bids, task_ids)
            self.blackboard.write(
                topic="awards",
                content=awards,
                author="system",
                stage="hungarian",
                metadata={"awarded_count": len(awards)},
            )
            timings["stage3_hungarian"] = time.time() - t0
            end_span(span, output=f"{len(awards)} tasks awarded")
        except Exception:
            end_span(span, error="hungarian failed")
            raise

        # Stage 4 — Awarded agents execute in parallel
        span = create_span("stage:execute", {"awarded": len(awards)})
        try:
            t0 = time.time()
            deliverables = await self._execute_awards(question, tasks, bids, awards)
            for task_id, content in deliverables.items():
                self.blackboard.write(
                    topic="deliverables",
                    content={"task_id": task_id, "content": content},
                    author=awards.get(task_id, "unknown"),
                    stage="execute",
                )
            timings["stage4_execute"] = time.time() - t0
            end_span(span, output=f"{len(deliverables)} deliverables")
        except Exception:
            end_span(span, error="execute failed")
            raise

        # Stage 5 — Mechanical assembly (concat in task-board order, no LLM)
        final_report = self._assemble_report(tasks, awards, deliverables)
        self.blackboard.write(
            topic="final_report",
            content=final_report,
            author="system",
            stage="assemble",
        )

        self.dump_audit_log(run_id)

        return ContractNetResult(
            question=question,
            tasks=tasks,
            bids=[
                {
                    "agent": b.agent,
                    "task_id": b.task_id,
                    "fit_score": b.fit_score,
                    "confidence": b.confidence,
                    "cost_estimate": b.cost_estimate,
                    "approach": b.approach,
                }
                for b in bids
            ],
            awards=awards,
            deliverables=deliverables,
            final_report=final_report,
            malformed_actions=[
                {"agent": m.agent, "error": m.error, "raw": m.raw} for m in malformed
            ],
            decentralization_manifest=self.decentralization_manifest(),
            timings=timings,
            run_id=run_id,
        )

    # ------------------------------------------------------------------
    # Internal stages
    # ------------------------------------------------------------------

    async def _split_tasks(self, question: str) -> list[dict[str, str]]:
        """Decompose question into 2-5 sub-tasks via a cheap parse-only LLM call.

        This is mechanical structure extraction, not content judgment.
        """
        prompt = TASK_SPLIT_PROMPT.replace("{question}", question)
        resp = await llm_complete(
            self.client,
            model=self.orchestration_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
            agent_name="task_split",
        )
        data = parse_json_object(extract_text(resp))
        raw_tasks = data.get("tasks", [])
        tasks: list[dict[str, str]] = []
        for i, t in enumerate(raw_tasks[:5]):
            if not isinstance(t, dict):
                continue
            tasks.append(
                {
                    "id": str(t.get("id") or f"t{i+1}"),
                    "title": str(t.get("title", "")).strip() or f"Task {i+1}",
                    "scope": str(t.get("scope", "")).strip(),
                }
            )
        if len(tasks) < 2:
            tasks = [
                {"id": "t1", "title": "Primary analysis", "scope": question[:200]},
                {"id": "t2", "title": "Risks and counter-arguments", "scope": "Surface key risks and counter-arguments."},
            ]
        return tasks

    async def _collect_bids(
        self, question: str, tasks: list[dict[str, str]]
    ) -> tuple[list[Bid], list[MalformedAction]]:
        task_board = "\n".join(
            f"  - [{t['id']}] {t['title']} — {t['scope']}" for t in tasks
        )
        other_agents = ", ".join(agent_name(a) for a in self.agents)

        async def _one(agent: Any) -> tuple[str, str]:
            from protocols.llm import agent_complete
            prompt = BID_PROMPT.format(
                agent_name=agent_name(agent),
                system_prompt=self._system_prompt(agent),
                task_board=task_board,
                other_agents=other_agents,
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
            return agent_name(agent), text

        raw = await asyncio.gather(
            *[_one(a) for a in self.agents], return_exceptions=True
        )

        bids: list[Bid] = []
        malformed: list[MalformedAction] = []
        for item in raw:
            if isinstance(item, BaseException):
                continue
            aname, text = item
            # Agents may emit multiple bid lines — split by line and parse each.
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                parsed = parse_bid(aname, line)
                if isinstance(parsed, Bid):
                    bids.append(parsed)
                elif isinstance(parsed, MalformedAction):
                    # Only log malformed if the line looked like it tried to be JSON
                    if line.startswith("{"):
                        malformed.append(parsed)
        return bids, malformed

    async def _execute_awards(
        self,
        question: str,
        tasks: list[dict[str, str]],
        bids: list[Bid],
        awards: dict[str, str],
    ) -> dict[str, str]:
        """Each awarded agent executes their assigned task. Parallel."""
        task_by_id = {t["id"]: t for t in tasks}
        bid_by_pair = {(b.agent, b.task_id): b for b in bids}

        async def _one(task_id: str, agent_name_str: str) -> tuple[str, str]:
            from protocols.llm import agent_complete
            agent = next(
                (a for a in self.agents if agent_name(a) == agent_name_str), None
            )
            if agent is None:
                return task_id, f"[no agent {agent_name_str}]"
            task = task_by_id[task_id]
            bid = bid_by_pair.get((agent_name_str, task_id))
            prompt = EXECUTE_PROMPT.format(
                agent_name=agent_name_str,
                system_prompt=self._system_prompt(agent),
                task_id=task_id,
                task_title=task["title"],
                task_scope=task["scope"],
                question=question,
                approach=bid.approach if bid else "(not specified)",
            )
            if hasattr(agent, "chat") and callable(agent.chat):
                text = await agent.chat(prompt)
            else:
                text = await agent_complete(
                    agent=agent,
                    fallback_model=self.thinking_model,
                    messages=[{"role": "user", "content": prompt}],
                    thinking_budget=0,
                    max_tokens=4096,
                    anthropic_client=self.client,
                )
            return task_id, text

        raw = await asyncio.gather(
            *[_one(tid, aname) for tid, aname in awards.items()],
            return_exceptions=True,
        )

        deliverables: dict[str, str] = {}
        for item in raw:
            if isinstance(item, BaseException):
                continue
            task_id, text = item
            deliverables[task_id] = text
        return deliverables

    def _assemble_report(
        self,
        tasks: list[dict[str, str]],
        awards: dict[str, str],
        deliverables: dict[str, str],
    ) -> str:
        """Deterministic markdown assembly. No LLM."""
        lines: list[str] = []
        for t in tasks:
            tid = t["id"]
            owner = awards.get(tid, "(no owner)")
            content = deliverables.get(tid, "(not delivered)")
            lines.append(f"## {t['title']}")
            lines.append(f"*Task `{tid}` — owner: **{owner}***\n")
            lines.append(content.strip())
            lines.append("")
        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def _system_prompt(agent: Any) -> str:
        if isinstance(agent, dict):
            return agent.get("system_prompt", "")
        return getattr(agent, "system_prompt", "") or ""
