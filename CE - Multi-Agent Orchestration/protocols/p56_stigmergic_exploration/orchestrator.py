"""P56: Stigmergic Exploration — Pheromone-biased path convergence.

Flow:
  Tick 0 (seed): each agent proposes K distinct candidate paths. All start at pheromone=1.0.
  Tick N (repeat):
    - Orchestrator decays all pheromones by decay_rate (mechanical, no LLM).
    - Each agent sees the sorted pheromone map and either reinforces an existing
      path, explores a new one, or halts.
    - Reinforcement multiplies that path's pheromone by boost. Explorations create
      new paths at pheromone=1.0.
    - Termination: (a) all agents halt, (b) top path dominance > threshold, or
      (c) max_ticks safety ceiling.
  Final: top-k paths by pheromone, with their refinement history.
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
    Explore,
    Halt,
    MalformedAction,
    Reinforce,
    agent_name,
    parse_stigmergic_action,
    pheromone_decay,
    pheromone_dominance,
    top_k_by_pheromone,
)
from protocols.langfuse_tracing import create_span, end_span, trace_protocol
from protocols.llm import agent_complete, parse_json_object
from protocols.tick_scheduler import TickOrchestrator

from .prompts import SEED_PROMPT, TICK_PROMPT


@dataclass
class Path:
    path_id: str
    description: str
    seeded_by: str
    refinements: list[dict[str, Any]] = field(default_factory=list)
    pheromone: float = 1.0


@dataclass
class StigmergicResult:
    question: str
    paths: list[dict[str, Any]]
    top_paths: list[dict[str, Any]]
    rounds: list[dict[str, Any]]  # per-round snapshot
    termination_reason: str  # "all_halted" | "dominance" | "max_ticks"
    dominance_final: float
    halts: list[dict[str, str]]
    malformed_actions: list[dict[str, str]]
    decentralization_manifest: dict[str, str]
    timings: dict[str, float] = field(default_factory=dict)
    run_id: str = ""


class StigmergicOrchestrator(TickOrchestrator):
    protocol_key = "p56_stigmergic_exploration"

    def __init__(
        self,
        agents: list[Any],
        *,
        thinking_model: str | None = None,
        orchestration_model: str | None = None,
        max_ticks: int = 4,
        seed_k: int = 2,
        decay_rate: float = 0.85,
        boost: float = 1.5,
        dominance_threshold: float = 0.5,
        top_k: int = 3,
    ) -> None:
        super().__init__(
            agents,
            thinking_model=thinking_model,
            orchestration_model=orchestration_model,
        )
        self.max_ticks = max_ticks
        self.seed_k = seed_k
        self.decay_rate = decay_rate
        self.boost = boost
        self.dominance_threshold = dominance_threshold
        self.top_k = top_k
        self._paths: dict[str, Path] = {}

    def decentralization_manifest(self) -> dict[str, str]:
        return {
            "control": "decentralized — agents self-select reinforce / explore / halt each tick",
            "information": "decentralized — full pheromone map shared with every agent",
            "communication": "decentralized — all actions written to Blackboard, peer-readable",
            "termination": "distributed predicate — pheromone-dominance threshold OR all-halt (with safety ceiling)",
        }

    def render_prompt_for(self, agent: Any, tick: int) -> str:
        raise NotImplementedError("P56 renders prompts inline in run()")

    @trace_protocol("p56_stigmergic_exploration")
    async def run(self, question: str) -> StigmergicResult:
        timings: dict[str, float] = {}
        run_id = uuid.uuid4().hex[:10]
        self.write_manifest()
        self.blackboard.write(
            topic="question", content=question, author="system", stage="init"
        )

        malformed_total: list[MalformedAction] = []
        halts_all: list[Halt] = []
        round_snapshots: list[dict[str, Any]] = []

        # Tick 0 — Seed K paths per agent
        span = create_span("tick:0_seed", {})
        try:
            t0 = time.time()
            await self._seed_paths(question)
            initial_ph = {pid: p.pheromone for pid, p in self._paths.items()}
            self.blackboard.write(
                topic="pheromone_map",
                content=initial_ph,
                author="system",
                stage="tick_0",
                metadata={"tick": 0, "dominance": pheromone_dominance(initial_ph)},
            )
            round_snapshots.append(
                {
                    "tick": 0,
                    "pheromone_map": initial_ph,
                    "dominance": pheromone_dominance(initial_ph),
                }
            )
            timings["tick_0_seed"] = time.time() - t0
            end_span(span, output=f"{len(self._paths)} paths seeded")
        except Exception:
            end_span(span, error="seed failed")
            raise

        # Tick N — iterate
        termination_reason = "max_ticks"
        for tick in range(1, self.max_ticks + 1):
            # Reset halts each tick (agents may re-engage)
            self._halted_agents.clear()

            # Mechanical decay
            decayed = pheromone_decay(
                {pid: p.pheromone for pid, p in self._paths.items()},
                self.decay_rate,
            )
            for pid, new_val in decayed.items():
                self._paths[pid].pheromone = new_val

            span = create_span(f"tick:{tick}", {})
            try:
                t0 = time.time()
                results, malformed = await self._run_tick(question, tick)
                for agent, action in results:
                    aname = agent_name(agent)
                    if isinstance(action, Reinforce):
                        if action.path_id in self._paths:
                            path = self._paths[action.path_id]
                            path.pheromone *= self.boost
                            path.refinements.append(
                                {"agent": aname, "refinement": action.refinement, "tick": tick}
                            )
                            self.blackboard.write(
                                topic="reinforce",
                                content={
                                    "agent": aname,
                                    "path_id": action.path_id,
                                    "refinement": action.refinement,
                                    "tick": tick,
                                    "new_pheromone": path.pheromone,
                                },
                                author=aname,
                                stage=f"tick_{tick}",
                            )
                        else:
                            malformed.append(
                                MalformedAction(
                                    agent=aname,
                                    raw=f"reinforce {action.path_id}",
                                    error=f"unknown path_id {action.path_id}",
                                )
                            )
                    elif isinstance(action, Explore):
                        new_path = Path(
                            path_id=action.path_id,
                            description=action.description,
                            seeded_by=aname,
                            pheromone=1.0,
                        )
                        self._paths[action.path_id] = new_path
                        self.blackboard.write(
                            topic="explore",
                            content={
                                "agent": aname,
                                "path_id": action.path_id,
                                "description": action.description,
                                "tick": tick,
                            },
                            author=aname,
                            stage=f"tick_{tick}",
                        )
                    elif isinstance(action, Halt):
                        halts_all.append(action)
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

                # Snapshot + termination checks
                ph = {pid: p.pheromone for pid, p in self._paths.items()}
                dom = pheromone_dominance(ph)
                self.blackboard.write(
                    topic="pheromone_map",
                    content=ph,
                    author="system",
                    stage=f"tick_{tick}",
                    metadata={"tick": tick, "dominance": dom},
                )
                round_snapshots.append(
                    {"tick": tick, "pheromone_map": ph, "dominance": dom}
                )
                timings[f"tick_{tick}"] = time.time() - t0
                end_span(span, output=f"dominance={dom:.2f}, paths={len(self._paths)}")
            except Exception:
                end_span(span, error=f"tick {tick} failed")
                raise

            if self.all_halted():
                termination_reason = "all_halted"
                break
            if dom > self.dominance_threshold:
                termination_reason = "dominance"
                break

        # Mechanical assembly
        final_ph = {pid: p.pheromone for pid, p in self._paths.items()}
        top_ids = [pid for pid, _ in top_k_by_pheromone(final_ph, k=self.top_k)]
        top_paths = [
            {
                "rank": i + 1,
                "path_id": pid,
                "pheromone": self._paths[pid].pheromone,
                "description": self._paths[pid].description,
                "seeded_by": self._paths[pid].seeded_by,
                "refinements": self._paths[pid].refinements,
            }
            for i, pid in enumerate(top_ids)
        ]
        self.blackboard.write(
            topic="convergence_report",
            content={"top_paths": top_paths, "dominance_final": pheromone_dominance(final_ph)},
            author="system",
            stage="assemble",
        )
        self.dump_audit_log(run_id)

        return StigmergicResult(
            question=question,
            paths=[
                {
                    "path_id": pid,
                    "description": p.description,
                    "seeded_by": p.seeded_by,
                    "pheromone": p.pheromone,
                    "refinements": p.refinements,
                }
                for pid, p in self._paths.items()
            ],
            top_paths=top_paths,
            rounds=round_snapshots,
            termination_reason=termination_reason,
            dominance_final=pheromone_dominance(final_ph),
            halts=[{"agent": h.agent, "reason": h.reason} for h in halts_all],
            malformed_actions=[
                {"agent": m.agent, "error": m.error, "raw": m.raw}
                for m in malformed_total
            ],
            decentralization_manifest=self.decentralization_manifest(),
            timings=timings,
            run_id=run_id,
        )

    # ------------------------------------------------------------------

    async def _seed_paths(self, question: str) -> None:
        async def _one(agent: Any) -> tuple[str, str]:
            prompt = SEED_PROMPT.format(
                agent_name=agent_name(agent),
                system_prompt=self._system_prompt(agent),
                question=question,
                k=self.seed_k,
            )
            if hasattr(agent, "chat") and callable(agent.chat):
                text = await agent.chat(prompt)
            else:
                text = await agent_complete(
                    agent=agent,
                    fallback_model=self.thinking_model,
                    messages=[{"role": "user", "content": prompt}],
                    thinking_budget=0,
                    max_tokens=1536,
                    anthropic_client=self.client,
                )
            return agent_name(agent), text

        raw = await asyncio.gather(
            *[_one(a) for a in self.agents], return_exceptions=True
        )

        for item in raw:
            if isinstance(item, BaseException):
                continue
            aname, text = item
            try:
                data = parse_json_object(text)
                paths = data.get("paths", [])
                if not isinstance(paths, list):
                    continue
                for p in paths[: self.seed_k]:
                    if not isinstance(p, dict):
                        continue
                    desc = str(p.get("description", "")).strip()
                    if not desc:
                        continue
                    pid = uuid.uuid4().hex[:10]
                    new_path = Path(
                        path_id=pid,
                        description=desc,
                        seeded_by=aname,
                        pheromone=1.0,
                    )
                    self._paths[pid] = new_path
                    self.blackboard.write(
                        topic="seed_path",
                        content={"path_id": pid, "description": desc, "agent": aname},
                        author=aname,
                        stage="tick_0",
                    )
            except Exception:
                continue

    async def _run_tick(
        self, question: str, tick: int
    ) -> tuple[list[tuple[Any, Any]], list[MalformedAction]]:
        pheromone_map = self._render_pheromone_map()

        async def _one(agent: Any) -> tuple[Any, str]:
            prompt = TICK_PROMPT.format(
                agent_name=agent_name(agent),
                system_prompt=self._system_prompt(agent),
                question=question,
                tick=tick,
                max_ticks=self.max_ticks,
                decay_rate=self.decay_rate,
                pheromone_map=pheromone_map,
            )
            if hasattr(agent, "chat") and callable(agent.chat):
                text = await agent.chat(prompt)
            else:
                text = await agent_complete(
                    agent=agent,
                    fallback_model=self.thinking_model,
                    messages=[{"role": "user", "content": prompt}],
                    thinking_budget=0,
                    max_tokens=1536,
                    anthropic_client=self.client,
                )
            return agent, text

        raw = await asyncio.gather(
            *[_one(a) for a in self.agents], return_exceptions=True
        )

        results: list[tuple[Any, Any]] = []
        malformed: list[MalformedAction] = []
        for item in raw:
            if isinstance(item, BaseException):
                continue
            agent, text = item
            aname = agent_name(agent)
            parsed = parse_stigmergic_action(aname, text)
            if isinstance(parsed, (Reinforce, Explore, Halt)):
                results.append((agent, parsed))
            else:
                malformed.append(parsed)
        return results, malformed

    def _render_pheromone_map(self) -> str:
        sorted_paths = sorted(
            self._paths.items(), key=lambda kv: (-kv[1].pheromone, kv[0])
        )
        lines: list[str] = []
        for pid, p in sorted_paths:
            lines.append(f"  [{pid}]  ph={p.pheromone:.2f}  (seeded by {p.seeded_by})")
            lines.append(f"          {p.description}")
            for r in p.refinements[-2:]:  # Show last 2 refinements
                lines.append(f"          ↳ {r['agent']} (t{r['tick']}): {r['refinement'][:150]}")
            lines.append("")
        return "\n".join(lines).strip() or "(no paths yet)"

    @staticmethod
    def _system_prompt(agent: Any) -> str:
        if isinstance(agent, dict):
            return agent.get("system_prompt", "")
        return getattr(agent, "system_prompt", "") or ""
