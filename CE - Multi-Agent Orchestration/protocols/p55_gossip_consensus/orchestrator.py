"""P55: Gossip Consensus — Random-pair pairwise convergence.

Flow:
  Round 0: each agent emits initial estimate (parallel, no peer info).
  Round N (repeat):
    - Orchestrator shuffles agents into random pairs (structural centralization,
      noted in the decentralization manifest — gossip requires random pairing).
    - Each agent sees its own last estimate + its partner's last estimate
      (pairwise-local, not full-shared) and emits an updated estimate.
    - Termination: population variance across all current estimates < epsilon
      OR max_rounds reached (safety ceiling, default 8).
  Final: confidence-weighted mean of the last-round estimates.

No synthesis. Termination is a deterministic predicate on agent-authored state.
"""

from __future__ import annotations

import asyncio
import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from protocols.decentralized_actions import (
    Estimate,
    MalformedAction,
    agent_name,
    confidence_weighted_mean,
    parse_estimate,
    population_variance,
)
from protocols.langfuse_tracing import create_span, end_span, trace_protocol
from protocols.llm import agent_complete
from protocols.tick_scheduler import TickOrchestrator

from .prompts import GOSSIP_EXCHANGE_PROMPT, INITIAL_ESTIMATE_PROMPT


@dataclass
class GossipResult:
    question: str
    units_note: str
    rounds: list[list[dict[str, Any]]]  # rounds[r] = [{agent, value, confidence, reasoning}, ...]
    pair_history: list[list[tuple[str, str]]]  # pair_history[r] = [(agent_a, agent_b), ...]
    variance_by_round: list[float]
    final_consensus: float
    convergence_reason: str  # "variance_threshold" | "max_rounds" | "single_agent"
    malformed_actions: list[dict[str, str]]
    decentralization_manifest: dict[str, str]
    timings: dict[str, float] = field(default_factory=dict)
    run_id: str = ""


class GossipOrchestrator(TickOrchestrator):
    protocol_key = "p55_gossip_consensus"

    def __init__(
        self,
        agents: list[Any],
        *,
        thinking_model: str | None = None,
        orchestration_model: str | None = None,
        max_rounds: int = 5,
        variance_epsilon: float = 0.25,
        rng_seed: int | None = None,
        units_note: str = "",
    ) -> None:
        super().__init__(
            agents,
            thinking_model=thinking_model,
            orchestration_model=orchestration_model,
        )
        self.max_rounds = max_rounds
        self.variance_epsilon = variance_epsilon
        self.rng = random.Random(rng_seed)
        self.units_note = units_note

    def decentralization_manifest(self) -> dict[str, str]:
        return {
            "control": "partially centralized — orchestrator performs random pairing (structural to gossip)",
            "information": "peer-local — agents see only their own and their partner's last estimate, not the full pool",
            "communication": "decentralized — pairwise exchanges written to Blackboard per round",
            "termination": "distributed predicate — population variance < epsilon on Blackboard-held state",
        }

    def render_prompt_for(self, agent: Any, tick: int) -> str:
        raise NotImplementedError("P55 renders prompts inline in run()")

    @trace_protocol("p55_gossip_consensus")
    async def run(self, question: str) -> GossipResult:
        timings: dict[str, float] = {}
        run_id = uuid.uuid4().hex[:10]
        self.write_manifest()
        self.blackboard.write(
            topic="question", content=question, author="system", stage="init"
        )
        if self.units_note:
            self.blackboard.write(
                topic="units_note", content=self.units_note, author="system", stage="init"
            )

        if len(self.agents) < 2:
            # Single-agent edge case — return whatever the one agent says.
            single = await self._round_zero(question)
            val = single[0].value if single else 0.0
            return GossipResult(
                question=question,
                units_note=self.units_note,
                rounds=[[self._est_dict(e) for e in single]],
                pair_history=[],
                variance_by_round=[0.0],
                final_consensus=val,
                convergence_reason="single_agent",
                malformed_actions=[],
                decentralization_manifest=self.decentralization_manifest(),
                timings=timings,
                run_id=run_id,
            )

        all_rounds: list[list[Estimate]] = []
        all_pairs: list[list[tuple[str, str]]] = []
        variances: list[float] = []
        malformed_total: list[MalformedAction] = []

        # Round 0 — initial estimates
        span = create_span("round:0_initial", {})
        try:
            t0 = time.time()
            round0, malformed0 = await self._round_zero_with_malformed(question)
            for e in round0:
                self.blackboard.write(
                    topic="estimates",
                    content={
                        "agent": e.agent,
                        "value": e.value,
                        "confidence": e.confidence,
                        "reasoning": e.reasoning,
                    },
                    author=e.agent,
                    stage="round_0",
                    metadata={"round": 0},
                )
            malformed_total.extend(malformed0)
            var0 = population_variance(round0)
            variances.append(var0)
            all_rounds.append(round0)
            all_pairs.append([])
            timings["round_0"] = time.time() - t0
            end_span(span, output=f"{len(round0)} estimates, variance={var0:.3f}")
        except Exception:
            end_span(span, error="round 0 failed")
            raise

        # Gossip rounds
        convergence_reason = "max_rounds"
        for r in range(1, self.max_rounds + 1):
            if variances[-1] < self.variance_epsilon:
                convergence_reason = "variance_threshold"
                break

            span = create_span(f"round:{r}_gossip", {})
            try:
                t0 = time.time()
                pairs = self._make_pairs(all_rounds[-1])
                all_pairs.append(pairs)
                new_round, malformed_r = await self._gossip_round(
                    question, all_rounds[-1], pairs, round_num=r
                )
                for e in new_round:
                    self.blackboard.write(
                        topic="estimates",
                        content={
                            "agent": e.agent,
                            "value": e.value,
                            "confidence": e.confidence,
                            "reasoning": e.reasoning,
                        },
                        author=e.agent,
                        stage=f"round_{r}",
                        metadata={"round": r},
                    )
                malformed_total.extend(malformed_r)
                var_r = population_variance(new_round)
                variances.append(var_r)
                all_rounds.append(new_round)
                timings[f"round_{r}"] = time.time() - t0
                end_span(span, output=f"variance={var_r:.3f}")
            except Exception:
                end_span(span, error=f"round {r} failed")
                raise

        final_value = confidence_weighted_mean(all_rounds[-1])
        self.blackboard.write(
            topic="consensus",
            content={
                "value": final_value,
                "variance": variances[-1],
                "convergence_reason": convergence_reason,
                "rounds_run": len(all_rounds) - 1,
            },
            author="system",
            stage="consensus",
        )
        self.dump_audit_log(run_id)

        return GossipResult(
            question=question,
            units_note=self.units_note,
            rounds=[[self._est_dict(e) for e in r] for r in all_rounds],
            pair_history=all_pairs,
            variance_by_round=variances,
            final_consensus=final_value,
            convergence_reason=convergence_reason,
            malformed_actions=[
                {"agent": m.agent, "error": m.error, "raw": m.raw}
                for m in malformed_total
            ],
            decentralization_manifest=self.decentralization_manifest(),
            timings=timings,
            run_id=run_id,
        )

    # ------------------------------------------------------------------

    def _units_text(self) -> str:
        if self.units_note:
            return f"NOTE ON UNITS / SCALE:\n{self.units_note}"
        return ""

    async def _round_zero(self, question: str) -> list[Estimate]:
        est, _ = await self._round_zero_with_malformed(question)
        return est

    async def _round_zero_with_malformed(
        self, question: str
    ) -> tuple[list[Estimate], list[MalformedAction]]:
        async def _one(agent: Any) -> tuple[str, str]:
            prompt = INITIAL_ESTIMATE_PROMPT.format(
                agent_name=agent_name(agent),
                system_prompt=self._system_prompt(agent),
                question=question,
                estimate_units_note=self._units_text(),
            )
            if hasattr(agent, "chat") and callable(agent.chat):
                text = await agent.chat(prompt)
            else:
                text = await agent_complete(
                    agent=agent,
                    fallback_model=self.thinking_model,
                    messages=[{"role": "user", "content": prompt}],
                    thinking_budget=0,
                    max_tokens=1024,
                    anthropic_client=self.client,
                )
            return agent_name(agent), text

        raw = await asyncio.gather(
            *[_one(a) for a in self.agents], return_exceptions=True
        )

        estimates: list[Estimate] = []
        malformed: list[MalformedAction] = []
        for item in raw:
            if isinstance(item, BaseException):
                continue
            aname, text = item
            parsed = parse_estimate(aname, text)
            if isinstance(parsed, Estimate):
                estimates.append(parsed)
            else:
                malformed.append(parsed)
        return estimates, malformed

    def _make_pairs(self, last_round: list[Estimate]) -> list[tuple[str, str]]:
        """Randomly pair active agents. Odd agent out is paired with themselves (no-op)."""
        names = [e.agent for e in last_round]
        self.rng.shuffle(names)
        pairs: list[tuple[str, str]] = []
        for i in range(0, len(names) - 1, 2):
            pairs.append((names[i], names[i + 1]))
        if len(names) % 2 == 1:
            pairs.append((names[-1], names[-1]))
        return pairs

    async def _gossip_round(
        self,
        question: str,
        last_round: list[Estimate],
        pairs: list[tuple[str, str]],
        round_num: int,
    ) -> tuple[list[Estimate], list[MalformedAction]]:
        by_name = {e.agent: e for e in last_round}
        agent_by_name = {agent_name(a): a for a in self.agents}

        async def _one(pair: tuple[str, str], who: str) -> tuple[str, str]:
            me_name, peer_name = (
                pair if pair[0] == who else (pair[1], pair[0])
            )
            me = by_name[me_name]
            peer = by_name[peer_name]
            agent = agent_by_name[me_name]
            prompt = GOSSIP_EXCHANGE_PROMPT.format(
                agent_name=me_name,
                system_prompt=self._system_prompt(agent),
                question=question,
                estimate_units_note=self._units_text(),
                my_value=me.value,
                my_confidence=me.confidence,
                my_reasoning=me.reasoning,
                peer_name=peer_name,
                peer_value=peer.value,
                peer_confidence=peer.confidence,
                peer_reasoning=peer.reasoning,
            )
            if hasattr(agent, "chat") and callable(agent.chat):
                text = await agent.chat(prompt)
            else:
                text = await agent_complete(
                    agent=agent,
                    fallback_model=self.thinking_model,
                    messages=[{"role": "user", "content": prompt}],
                    thinking_budget=0,
                    max_tokens=1024,
                    anthropic_client=self.client,
                )
            return me_name, text

        coros = []
        for pair in pairs:
            if pair[0] == pair[1]:
                # Odd agent out: carry previous estimate verbatim
                continue
            coros.append(_one(pair, pair[0]))
            coros.append(_one(pair, pair[1]))

        raw = await asyncio.gather(*coros, return_exceptions=True)
        estimates: list[Estimate] = []
        malformed: list[MalformedAction] = []
        seen_agents: set[str] = set()
        for item in raw:
            if isinstance(item, BaseException):
                continue
            aname, text = item
            parsed = parse_estimate(aname, text)
            if isinstance(parsed, Estimate):
                estimates.append(parsed)
                seen_agents.add(aname)
            else:
                malformed.append(parsed)

        # Carry forward any agents who were odd-one-out or whose response was malformed
        for e in last_round:
            if e.agent not in seen_agents:
                estimates.append(e)
        return estimates, malformed

    @staticmethod
    def _est_dict(e: Estimate) -> dict[str, Any]:
        return {
            "agent": e.agent,
            "value": e.value,
            "confidence": e.confidence,
            "reasoning": e.reasoning,
        }

    @staticmethod
    def _system_prompt(agent: Any) -> str:
        if isinstance(agent, dict):
            return agent.get("system_prompt", "")
        return getattr(agent, "system_prompt", "") or ""
