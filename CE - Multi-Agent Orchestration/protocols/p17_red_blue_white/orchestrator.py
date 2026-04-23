"""P17: Red/Blue/White Team — Orchestrator.

Adversarial stress-testing: Red attacks, Blue defends, White adjudicates.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from protocols.langfuse_tracing import trace_protocol, create_span, end_span
from protocols.llm import agent_complete, parse_json_object, filter_exceptions

from protocols.scoping import filter_context_for_agent, tag_context
from protocols.tracing import make_client
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from .prompts import (
    RED_ATTACK_PROMPT,
    BLUE_DEFENSE_PROMPT,
    WHITE_ADJUDICATE_PROMPT,
    FINAL_ASSESSMENT_PROMPT,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Attack:
    agent: str
    vulnerabilities: list[dict[str, str]]


@dataclass
class Defense:
    agent: str
    mitigations: list[dict[str, str]]


@dataclass
class Adjudication:
    vulnerability_id: str
    vulnerability_title: str
    severity: str
    verdict: str  # Resolved | Partially Resolved | Open
    reasoning: str
    defense_gaps: str
    recommended_action: str


@dataclass
class RedBlueWhiteResult:
    question: str
    plan: str
    attacks: list[Attack]
    defenses: list[Defense]
    adjudication: list[Adjudication]
    resolved_risks: list[dict[str, str]]
    open_risks: list[dict[str, str]]
    plan_strength_score: int
    recommendations: list[str]
    timings: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Team assignment
# ---------------------------------------------------------------------------

# Canonical role hints. Extend these sets as new agent archetypes are added.
_RED_HINTS = {
    "cmo", "cfo", "cro",
    "gtm-cro", "gtm-vp-sales",
    "vc-app-investor", "vc-infra-investor",
}
_BLUE_HINTS = {
    "cto", "coo", "cpo",
    "cpo-service-designer", "coo-process-builder",
}
_WHITE_HINTS = {"ceo", "ceo-board-prep"}


def _agent_key(agent: dict[str, Any]) -> str:
    return str(agent.get("key") or agent.get("name") or "").lower()


def _assign_teams(
    agents: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Split a flat agent roster into (red, blue, white).

    Strategy: first pass matches each agent against role-hint sets keyed on
    agent name. Anything unmatched is distributed positionally — unmatched
    items go to the smaller of red/blue, and the last unmatched slot fills
    white if it is still empty. Guarantees all three roles are populated
    whenever at least three agents are provided; with fewer than three, falls
    back to cycling the available agents.
    """
    if not agents:
        raise ValueError("p17 team assignment requires at least one agent")

    red: list[dict[str, Any]] = []
    blue: list[dict[str, Any]] = []
    white: dict[str, Any] | None = None
    remaining: list[dict[str, Any]] = []

    for a in agents:
        key = _agent_key(a)
        if key in _WHITE_HINTS and white is None:
            white = a
        elif key in _RED_HINTS:
            red.append(a)
        elif key in _BLUE_HINTS:
            blue.append(a)
        else:
            remaining.append(a)

    # Fill gaps positionally. Reserve the last unmatched item for white if
    # white is still empty and both other teams already have at least one.
    while remaining:
        nxt = remaining.pop(0)
        if white is None and not remaining and red and blue:
            white = nxt
            break
        if len(red) <= len(blue):
            red.append(nxt)
        else:
            blue.append(nxt)

    # If we still have no white (e.g., all agents matched red/blue hints),
    # promote from the bigger team.
    if white is None:
        donor = red if len(red) > len(blue) else blue
        if donor:
            white = donor.pop()

    # If a team is still empty (very small rosters), cycle from whatever
    # is populated to keep the contract valid.
    pool = [a for group in ([white] if white else [], red, blue) for a in group]
    if not pool:
        raise ValueError("p17 team assignment failed: no agents available")
    if white is None:
        white = pool[0]
    if not red:
        red = [pool[0]]
    if not blue:
        blue = [pool[-1]]

    return red, blue, white


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class RedBlueWhiteOrchestrator:
    """Runs the four-phase Red/Blue/White team protocol."""

    thinking_model: str = THINKING_MODEL
    orchestration_model: str = ORCHESTRATION_MODEL

    def __init__(
        self,
        red_agents: list[dict[str, str]] | None = None,
        blue_agents: list[dict[str, str]] | None = None,
        white_agent: dict[str, str] | None = None,
        *,
        agents: list[dict[str, Any]] | None = None,
        thinking_model: str | None = None,
        orchestration_model: str | None = None,
        trace: bool = False,
        trace_path: str | None = None,
    ) -> None:
        if agents and not (red_agents or blue_agents or white_agent):
            red_agents, blue_agents, white_agent = _assign_teams(agents)
            print(
                f"[p17] Auto-assigned teams from flat roster: "
                f"red={[_agent_key(a) for a in red_agents]} "
                f"blue={[_agent_key(a) for a in blue_agents]} "
                f"white={_agent_key(white_agent)}",
                flush=True,
            )
        if not red_agents or not blue_agents or not white_agent:
            raise ValueError(
                "p17 requires either explicit red_agents + blue_agents + white_agent, "
                "or a flat `agents` list with enough agents to populate all three roles."
            )
        self.red_agents = red_agents
        self.blue_agents = blue_agents
        self.white_agent = white_agent
        if thinking_model:
            self.thinking_model = thinking_model
        if orchestration_model:
            self.orchestration_model = orchestration_model
        self.client = make_client(protocol_id="p17_red_blue_white", trace=trace, trace_path=Path(trace_path) if trace_path else None)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    @trace_protocol("p17_red_blue_white")
    async def run(
        self,
        question: str,
        plan: str | None = None,
    ) -> RedBlueWhiteResult:
        # API runner invokes `run(question)` — when no explicit plan is passed,
        # treat the question itself as the plan/proposal to stress-test.
        if plan is None or not plan.strip():
            plan = question
        timings: dict[str, float] = {}

        # Phase 1 — Red Team Attack
        t0 = time.time()
        span = create_span("stage:red_team_attack", {"agent_count": len(self.red_agents)})
        try:
            attacks = await self._red_team_attack(question, plan)
            end_span(span, output=f"{sum(len(a.vulnerabilities) for a in attacks)} vulnerabilities")
        except Exception:
            end_span(span, error="red_team_attack failed")
            raise
        timings["phase1_red_attack"] = time.time() - t0

        # Phase 2 — Blue Team Defense
        t0 = time.time()
        span = create_span("stage:blue_team_defense", {"agent_count": len(self.blue_agents)})
        try:
            defenses = await self._blue_team_defense(question, plan, attacks)
            end_span(span, output=f"{sum(len(d.mitigations) for d in defenses)} mitigations")
        except Exception:
            end_span(span, error="blue_team_defense failed")
            raise
        timings["phase2_blue_defense"] = time.time() - t0

        # Phase 3 — White Team Adjudication
        t0 = time.time()
        span = create_span("stage:white_adjudication", {})
        try:
            adjudication = await self._white_team_adjudicate(question, plan, attacks, defenses)
            end_span(span, output=f"{len(adjudication)} adjudications")
        except Exception:
            end_span(span, error="white_adjudication failed")
            raise
        timings["phase3_white_adjudicate"] = time.time() - t0

        # Phase 4 — Final Assessment
        t0 = time.time()
        span = create_span("stage:final_assessment", {})
        try:
            final = await self._final_assessment(question, plan, adjudication)
            end_span(span, output=f"score={final.get('plan_strength_score', '?')}")
        except Exception:
            end_span(span, error="final_assessment failed")
            raise
        timings["phase4_final_assessment"] = time.time() - t0

        return RedBlueWhiteResult(
            question=question,
            plan=plan,
            attacks=attacks,
            defenses=defenses,
            adjudication=adjudication,
            resolved_risks=final.get("resolved_risks", []),
            open_risks=final.get("open_risks", []),
            plan_strength_score=final.get("plan_strength_score", 0),
            recommendations=final.get("recommendations", []),
            timings=timings,
        )

    # ------------------------------------------------------------------
    # Phase 1: Red Team Attack
    # ------------------------------------------------------------------

    async def _red_team_attack(self, question: str, plan: str) -> list[Attack]:
        """Each Red agent independently identifies vulnerabilities (parallel, Opus)."""

        async def _one(agent: dict) -> Attack:
            prompt = RED_ATTACK_PROMPT.format(
                question=question,
                plan=plan,
                agent_name=agent["name"],
                system_prompt=agent["system_prompt"],
            )
            text = await agent_complete(
                agent=agent,
                fallback_model=self.thinking_model,
                messages=[{"role": "user", "content": prompt}],
                thinking_budget=8192,
                anthropic_client=self.client,
            )
            parsed = parse_json_object(text)
            return Attack(
                agent=parsed.get("agent", agent["name"]),
                vulnerabilities=parsed.get("vulnerabilities", []),
            )

        results = await asyncio.gather(*[_one(a) for a in self.red_agents], return_exceptions=True)
        results = filter_exceptions(results, label="p17_red_blue_white")
        return list(results)

    # ------------------------------------------------------------------
    # Phase 2: Blue Team Defense
    # ------------------------------------------------------------------

    async def _blue_team_defense(
        self, question: str, plan: str, attacks: list[Attack],
    ) -> list[Defense]:
        """Each Blue agent receives scoped attacks and produces defenses (parallel, Opus)."""
        attacks_block = self._format_attacks_block(attacks)
        # Build scoped context blocks from attacks
        attack_context_blocks = []
        for attack in attacks:
            for v in attack.vulnerabilities:
                scope = "all"  # attacks are generally visible to all defenders
                attack_context_blocks.append(tag_context(
                    f"[{v.get('id', '?')}] ({v.get('severity', '?')}) {v.get('title', '')} — from {attack.agent}\n"
                    f"  Description: {v.get('description', '')}\n"
                    f"  Failure scenario: {v.get('failure_scenario', '')}",
                    scope,
                ))

        async def _one(agent: dict) -> Defense:
            scoped_attacks = filter_context_for_agent(agent, attack_context_blocks) if attack_context_blocks else attacks_block
            prompt = BLUE_DEFENSE_PROMPT.format(
                question=question,
                plan=plan,
                agent_name=agent["name"],
                system_prompt=agent["system_prompt"],
                attacks_block=scoped_attacks,
            )
            text = await agent_complete(
                agent=agent,
                fallback_model=self.thinking_model,
                messages=[{"role": "user", "content": prompt}],
                thinking_budget=8192,
                anthropic_client=self.client,
            )
            parsed = parse_json_object(text)
            return Defense(
                agent=parsed.get("agent", agent["name"]),
                mitigations=parsed.get("mitigations", []),
            )

        results = await asyncio.gather(*[_one(a) for a in self.blue_agents], return_exceptions=True)
        results = filter_exceptions(results, label="p17_red_blue_white")
        return list(results)

    # ------------------------------------------------------------------
    # Phase 3: White Team Adjudication
    # ------------------------------------------------------------------

    async def _white_team_adjudicate(
        self,
        question: str,
        plan: str,
        attacks: list[Attack],
        defenses: list[Defense],
    ) -> list[Adjudication]:
        """White agent evaluates each attack/defense pair (Opus with thinking)."""
        attacks_block = self._format_attacks_block(attacks)
        defenses_block = self._format_defenses_block(defenses)

        prompt = WHITE_ADJUDICATE_PROMPT.format(
            question=question,
            plan=plan,
            attacks_block=attacks_block,
            defenses_block=defenses_block,
        )
        text = await agent_complete(
            agent=self.white_agent,
            fallback_model=self.thinking_model,
            messages=[{"role": "user", "content": prompt}],
            thinking_budget=10000,
            max_tokens=14096,
            anthropic_client=self.client,
        )
        parsed = parse_json_object(text)

        adjudications = []
        for item in parsed.get("adjudications", []):
            adjudications.append(Adjudication(
                vulnerability_id=item.get("vulnerability_id", ""),
                vulnerability_title=item.get("vulnerability_title", ""),
                severity=item.get("severity", "Medium"),
                verdict=item.get("verdict", "Open"),
                reasoning=item.get("reasoning", ""),
                defense_gaps=item.get("defense_gaps", ""),
                recommended_action=item.get("recommended_action", ""),
            ))
        return adjudications

    # ------------------------------------------------------------------
    # Phase 4: Final Assessment
    # ------------------------------------------------------------------

    async def _final_assessment(
        self,
        question: str,
        plan: str,
        adjudication: list[Adjudication],
    ) -> dict[str, Any]:
        """White agent synthesizes final report (Opus)."""
        adjudication_block = self._format_adjudication_block(adjudication)

        prompt = FINAL_ASSESSMENT_PROMPT.format(
            question=question,
            plan=plan,
            adjudication_block=adjudication_block,
        )
        text = await agent_complete(
            agent=self.white_agent,
            fallback_model=self.thinking_model,
            messages=[{"role": "user", "content": prompt}],
            thinking_budget=0,
            max_tokens=4096,
            anthropic_client=self.client,
        )
        return parse_json_object(text)

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_attacks_block(attacks: list[Attack]) -> str:
        lines = []
        for attack in attacks:
            for v in attack.vulnerabilities:
                vid = v.get("id", "?")
                sev = v.get("severity", "?")
                title = v.get("title", "untitled")
                desc = v.get("description", "")
                scenario = v.get("failure_scenario", "")
                lines.append(
                    f"[{vid}] ({sev}) {title} — from {attack.agent}\n"
                    f"  Description: {desc}\n"
                    f"  Failure scenario: {scenario}"
                )
        return "\n\n".join(lines) if lines else "No attacks identified."

    @staticmethod
    def _format_defenses_block(defenses: list[Defense]) -> str:
        lines = []
        for defense in defenses:
            for m in defense.mitigations:
                vid = m.get("vulnerability_id", "?")
                dtype = m.get("defense_type", "?")
                response = m.get("response", "")
                evidence = m.get("evidence", "")
                residual = m.get("residual_risk", "")
                lines.append(
                    f"Defense for {vid} ({dtype}) — from {defense.agent}\n"
                    f"  Response: {response}\n"
                    f"  Evidence: {evidence}\n"
                    f"  Residual risk: {residual}"
                )
        return "\n\n".join(lines) if lines else "No defenses provided."

    @staticmethod
    def _format_adjudication_block(adjudication: list[Adjudication]) -> str:
        lines = []
        for adj in adjudication:
            lines.append(
                f"[{adj.vulnerability_id}] {adj.vulnerability_title} "
                f"(severity: {adj.severity})\n"
                f"  Verdict: {adj.verdict}\n"
                f"  Reasoning: {adj.reasoning}\n"
                f"  Defense gaps: {adj.defense_gaps}\n"
                f"  Recommended action: {adj.recommended_action}"
            )
        return "\n\n".join(lines) if lines else "No adjudications."

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------


