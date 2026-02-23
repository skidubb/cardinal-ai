"""P17: Red/Blue/White Team — Orchestrator.

Adversarial stress-testing: Red attacks, Blue defends, White adjudicates.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

import anthropic

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
# Orchestrator
# ---------------------------------------------------------------------------

class RedBlueWhiteOrchestrator:
    """Runs the four-phase Red/Blue/White team protocol."""

    thinking_model: str = "claude-opus-4-6"
    orchestration_model: str = "claude-haiku-4-5-20251001"

    def __init__(
        self,
        red_agents: list[dict[str, str]],
        blue_agents: list[dict[str, str]],
        white_agent: dict[str, str],
        *,
        thinking_model: str | None = None,
        orchestration_model: str | None = None,
    ) -> None:
        self.red_agents = red_agents
        self.blue_agents = blue_agents
        self.white_agent = white_agent
        if thinking_model:
            self.thinking_model = thinking_model
        if orchestration_model:
            self.orchestration_model = orchestration_model
        self.client = anthropic.AsyncAnthropic()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def run(self, question: str, plan: str) -> RedBlueWhiteResult:
        timings: dict[str, float] = {}

        # Phase 1 — Red Team Attack
        t0 = time.time()
        attacks = await self._red_team_attack(question, plan)
        timings["phase1_red_attack"] = time.time() - t0

        # Phase 2 — Blue Team Defense
        t0 = time.time()
        defenses = await self._blue_team_defense(question, plan, attacks)
        timings["phase2_blue_defense"] = time.time() - t0

        # Phase 3 — White Team Adjudication
        t0 = time.time()
        adjudication = await self._white_team_adjudicate(question, plan, attacks, defenses)
        timings["phase3_white_adjudicate"] = time.time() - t0

        # Phase 4 — Final Assessment
        t0 = time.time()
        final = await self._final_assessment(question, plan, adjudication)
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
            resp = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=12288,
                thinking={
                    "type": "enabled",
                    "budget_tokens": 8192,
                },
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = self._parse_json_object(self._extract_text(resp))
            return Attack(
                agent=parsed.get("agent", agent["name"]),
                vulnerabilities=parsed.get("vulnerabilities", []),
            )

        results = await asyncio.gather(*[_one(a) for a in self.red_agents])
        return list(results)

    # ------------------------------------------------------------------
    # Phase 2: Blue Team Defense
    # ------------------------------------------------------------------

    async def _blue_team_defense(
        self, question: str, plan: str, attacks: list[Attack],
    ) -> list[Defense]:
        """Each Blue agent receives ALL attacks and produces defenses (parallel, Opus)."""
        attacks_block = self._format_attacks_block(attacks)

        async def _one(agent: dict) -> Defense:
            prompt = BLUE_DEFENSE_PROMPT.format(
                question=question,
                plan=plan,
                agent_name=agent["name"],
                system_prompt=agent["system_prompt"],
                attacks_block=attacks_block,
            )
            resp = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=12288,
                thinking={
                    "type": "enabled",
                    "budget_tokens": 8192,
                },
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = self._parse_json_object(self._extract_text(resp))
            return Defense(
                agent=parsed.get("agent", agent["name"]),
                mitigations=parsed.get("mitigations", []),
            )

        results = await asyncio.gather(*[_one(a) for a in self.blue_agents])
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
        resp = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=14096,
            thinking={
                "type": "enabled",
                "budget_tokens": 10000,
            },
            messages=[{"role": "user", "content": prompt}],
        )
        parsed = self._parse_json_object(self._extract_text(resp))

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
        resp = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._parse_json_object(self._extract_text(resp))

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

    @staticmethod
    def _extract_text(response: anthropic.types.Message) -> str:
        parts = []
        for block in response.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "\n".join(parts)

    @staticmethod
    def _parse_json_object(text: str) -> dict:
        """Extract the first JSON object from text."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {}
