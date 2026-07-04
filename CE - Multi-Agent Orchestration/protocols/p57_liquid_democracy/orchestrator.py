"""P57: Liquid Democracy — Delegation-based weighted Borda voting.

Flow:
  1. Tick 1: each agent proposes 1-3 candidate options (parallel).
  2. Mechanical dedup: string-normalize + fuzzy dedup (no LLM judgment).
  3. Tick 2: each agent either VOTES (ranks options) or DELEGATES (names a peer).
  4. Mechanical resolution: delegation chains → effective votes, then weighted Borda.
  5. Final answer = top option verbatim. No synthesis.
"""

from __future__ import annotations

import asyncio
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ce_shared.env import find_and_load_dotenv

find_and_load_dotenv()  # Must run before langfuse_tracing import so LANGFUSE_SECRET_KEY is visible.

from protocols.decentralized_actions import (
    Delegation,
    MalformedAction,
    Vote,
    agent_name,
    parse_vote_or_delegate,
    resolve_delegations,
    weighted_borda,
)
from protocols.langfuse_tracing import create_span, end_span, trace_protocol
from protocols.llm import agent_complete, parse_json_object
from protocols.tick_scheduler import TickOrchestrator

from .prompts import PROPOSE_PROMPT, VOTE_OR_DELEGATE_PROMPT


@dataclass
class LiquidDemocracyResult:
    question: str
    proposals: list[dict[str, Any]]
    ballot: list[dict[str, str]]
    votes: list[dict[str, Any]]
    delegations: list[dict[str, str]]
    effective_votes: dict[str, list[str]]
    delegation_chains: dict[str, list[str]]
    borda_scores: list[tuple[str, float]]
    winner_id: str
    winner_label: str
    malformed_actions: list[dict[str, str]]
    decentralization_manifest: dict[str, str]
    timings: dict[str, float] = field(default_factory=dict)
    run_id: str = ""


class LiquidDemocracyOrchestrator(TickOrchestrator):
    protocol_key = "p57_liquid_democracy"

    def decentralization_manifest(self) -> dict[str, str]:
        return {
            "control": "decentralized — each agent chooses to vote or delegate",
            "information": "decentralized — full option pool and peer list shared on the Blackboard",
            "communication": "decentralized — agents exchange via Blackboard entries",
            "termination": "distributed quorum — protocol ends when every agent emits vote or delegation",
        }

    def render_prompt_for(self, agent: Any, tick: int) -> str:
        raise NotImplementedError("P57 renders prompts inline in run()")

    @trace_protocol("p57_liquid_democracy")
    async def run(self, question: str) -> LiquidDemocracyResult:
        timings: dict[str, float] = {}
        run_id = uuid.uuid4().hex[:10]
        self.write_manifest()
        self.blackboard.write(
            topic="question", content=question, author="system", stage="init"
        )

        # Stage 1 — Proposals (parallel)
        span = create_span("stage:propose", {"agent_count": len(self.agents)})
        try:
            t0 = time.time()
            proposals = await self._collect_proposals(question)
            for p in proposals:
                self.blackboard.write(
                    topic="option",
                    content=p,
                    author=p["agent"],
                    stage="propose",
                )
            timings["stage1_propose"] = time.time() - t0
            end_span(span, output=f"{len(proposals)} proposals")
        except Exception:
            end_span(span, error="propose failed")
            raise

        # Stage 2 — Mechanical dedup
        ballot = self._dedup_options(proposals)
        self.blackboard.write(
            topic="ballot_options", content=ballot, author="system", stage="dedup",
            metadata={"option_count": len(ballot)},
        )
        option_ids = [b["id"] for b in ballot]

        # Stage 3 — Vote or Delegate (parallel)
        span = create_span("stage:vote_or_delegate", {})
        try:
            t0 = time.time()
            votes, delegations, malformed = await self._collect_votes(
                question, ballot
            )
            for v in votes:
                self.blackboard.write(
                    topic="votes",
                    content={"agent": v.agent, "ranking": v.ranking},
                    author=v.agent,
                    stage="vote",
                )
            for d in delegations:
                self.blackboard.write(
                    topic="delegations",
                    content={"agent": d.agent, "to": d.to, "topic": d.topic},
                    author=d.agent,
                    stage="delegate",
                )
            for m in malformed:
                self.blackboard.write(
                    topic="malformed_actions",
                    content={"agent": m.agent, "error": m.error, "raw": m.raw},
                    author=m.agent,
                    stage="vote_or_delegate",
                )
            timings["stage3_vote_delegate"] = time.time() - t0
            end_span(
                span,
                output=f"{len(votes)} votes, {len(delegations)} delegations, {len(malformed)} malformed",
            )
        except Exception:
            end_span(span, error="vote_or_delegate failed")
            raise

        # Stage 4 — Mechanical delegation resolution + weighted Borda
        effective, chains = resolve_delegations(votes, delegations)
        self.blackboard.write(
            topic="effective_votes",
            content={a: v.ranking for a, v in effective.items()},
            author="system",
            stage="resolve",
        )
        self.blackboard.write(
            topic="delegation_chains", content=chains, author="system", stage="resolve"
        )

        scores = weighted_borda(effective, option_ids)
        self.blackboard.write(
            topic="tally",
            content={"scores": scores, "winner": scores[0][0] if scores else ""},
            author="system",
            stage="tally",
        )

        winner_id = scores[0][0] if scores else ""
        winner_label = next(
            (b["label"] for b in ballot if b["id"] == winner_id), ""
        )

        self.dump_audit_log(run_id)

        return LiquidDemocracyResult(
            question=question,
            proposals=proposals,
            ballot=ballot,
            votes=[{"agent": v.agent, "ranking": v.ranking} for v in votes],
            delegations=[
                {"agent": d.agent, "to": d.to, "topic": d.topic} for d in delegations
            ],
            effective_votes={a: v.ranking for a, v in effective.items()},
            delegation_chains=chains,
            borda_scores=scores,
            winner_id=winner_id,
            winner_label=winner_label,
            malformed_actions=[
                {"agent": m.agent, "error": m.error, "raw": m.raw} for m in malformed
            ],
            decentralization_manifest=self.decentralization_manifest(),
            timings=timings,
            run_id=run_id,
        )

    # ------------------------------------------------------------------

    async def _collect_proposals(self, question: str) -> list[dict[str, Any]]:
        async def _one(agent: Any) -> tuple[str, str]:
            prompt = PROPOSE_PROMPT.format(
                agent_name=agent_name(agent),
                system_prompt=self._system_prompt(agent),
                question=question,
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

        proposals: list[dict[str, Any]] = []
        for item in raw:
            if isinstance(item, BaseException):
                continue
            aname, text = item
            try:
                data = parse_json_object(text)
                options = data.get("options", [])
                if not isinstance(options, list):
                    continue
                for opt in options[:3]:
                    if not isinstance(opt, dict):
                        continue
                    label = str(opt.get("label", "")).strip()
                    if label:
                        proposals.append(
                            {
                                "agent": aname,
                                "label": label,
                                "rationale": str(opt.get("rationale", "")).strip(),
                            }
                        )
            except Exception:
                continue
        return proposals

    @staticmethod
    def _normalize(s: str) -> str:
        """Lowercase, strip, collapse whitespace, drop non-alphanumerics (for dedup only)."""
        s = s.lower().strip()
        s = re.sub(r"[^a-z0-9 ]+", "", s)
        s = re.sub(r"\s+", " ", s)
        return s

    def _dedup_options(
        self, proposals: list[dict[str, Any]]
    ) -> list[dict[str, str]]:
        """String-normalize + first-token prefix dedup. Deterministic, no LLM."""
        seen: dict[str, dict[str, Any]] = {}
        for p in proposals:
            key = self._normalize(p["label"])
            if not key:
                continue
            # Collapse near-duplicates by first 6 normalized words
            short_key = " ".join(key.split()[:6])
            if short_key in seen:
                seen[short_key]["proposers"].append(p["agent"])
                seen[short_key]["rationales"].append(p["rationale"])
                continue
            seen[short_key] = {
                "label": p["label"],
                "proposers": [p["agent"]],
                "rationales": [p["rationale"]],
            }
        ballot: list[dict[str, str]] = []
        for i, (_, item) in enumerate(seen.items()):
            ballot.append(
                {
                    "id": f"opt_{i+1}",
                    "label": item["label"],
                    "proposers": item["proposers"],
                    "rationales": item["rationales"],
                }
            )
        return ballot

    async def _collect_votes(
        self, question: str, ballot: list[dict[str, str]]
    ) -> tuple[list[Vote], list[Delegation], list[MalformedAction]]:
        ballot_block = "\n".join(
            f"  - [{b['id']}] {b['label']}  (proposed by: {', '.join(b['proposers'])})"
            for b in ballot
        )
        peer_block = "\n".join(
            f"  - {agent_name(a)}: {self._short_role(a)}" for a in self.agents
        )
        option_ids = {b["id"] for b in ballot}

        async def _one(agent: Any) -> tuple[str, str]:
            prompt = VOTE_OR_DELEGATE_PROMPT.format(
                agent_name=agent_name(agent),
                system_prompt=self._system_prompt(agent),
                question=question,
                ballot_block=ballot_block,
                peer_block=peer_block,
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

        votes: list[Vote] = []
        delegations: list[Delegation] = []
        malformed: list[MalformedAction] = []
        agent_names = {agent_name(a) for a in self.agents}
        for item in raw:
            if isinstance(item, BaseException):
                continue
            aname, text = item
            parsed = parse_vote_or_delegate(aname, text)
            if isinstance(parsed, Vote):
                # Validate ranking references actual option ids
                ranking = [opt for opt in parsed.ranking if opt in option_ids]
                if ranking:
                    votes.append(Vote(agent=aname, ranking=ranking))
                else:
                    malformed.append(
                        MalformedAction(
                            agent=aname, raw=text[:500], error="vote had no valid option ids"
                        )
                    )
            elif isinstance(parsed, Delegation):
                if parsed.to in agent_names and parsed.to != aname:
                    delegations.append(parsed)
                else:
                    malformed.append(
                        MalformedAction(
                            agent=aname,
                            raw=text[:500],
                            error=f"delegate target {parsed.to!r} not in agent pool",
                        )
                    )
            else:
                malformed.append(parsed)
        return votes, delegations, malformed

    @staticmethod
    def _short_role(agent: Any) -> str:
        name = agent_name(agent)
        return name  # simple — the name itself is the role label in the Cardinal registry

    @staticmethod
    def _system_prompt(agent: Any) -> str:
        if isinstance(agent, dict):
            return agent.get("system_prompt", "")
        return getattr(agent, "system_prompt", "") or ""
