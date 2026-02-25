"""Airport 5G Pipeline Orchestrator — chains P14 → P16 → P5 → P17.

Each stage's output feeds the next, producing a complete decision-making
story from discovery through stress-tested recommendation.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
load_dotenv()

import anthropic

from protocols.scoping import build_context_blocks, filter_context_for_agent, get_primary_scope
from protocols.tracing import make_client
from protocols.p05_constraint_negotiation.constraints import ConstraintExtractor, ConstraintStore

from .prompts import (
    DISCOVER_SOLO_PROMPT,
    DISCOVER_PAIR_MERGE_PROMPT,
    DISCOVER_SYNTHESIS_PROMPT,
    ACH_HYPOTHESIS_PROMPT,
    ACH_SYNTHESIS_PROMPT,
    NEGOTIATE_OPENING_PROMPT,
    NEGOTIATE_REVISION_PROMPT,
    NEGOTIATE_SYNTHESIS_PROMPT,
    STRESS_RED_PROMPT,
    STRESS_BLUE_PROMPT,
    STRESS_WHITE_PROMPT,
)
from .team_assignment import assign_teams


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class StageResult:
    stage_name: str
    output: str
    raw_data: dict[str, Any] = field(default_factory=dict)
    elapsed_seconds: float = 0.0


@dataclass
class PipelineResult:
    question: str
    stages: list[StageResult] = field(default_factory=list)
    final_recommendation: str = ""
    total_elapsed: float = 0.0


# Default hypotheses if Stage 1 doesn't generate them
DEFAULT_HYPOTHESES = [
    {"id": "H1", "label": "AT&T-Led Expansion", "description": "Extend existing CWP to cover all use cases. AT&T owns/operates. Airport pays subscription."},
    {"id": "H2", "label": "Airport-Sovereign Network", "description": "DFW builds and owns the entire private 5G infrastructure. AT&T becomes one tenant."},
    {"id": "H3", "label": "Hybrid Co-Investment", "description": "DFW owns infrastructure, AT&T operates carrier layer, revenue share on tenant access."},
    {"id": "H4", "label": "Phased Sovereignty", "description": "Start with AT&T-led (terminals A/B/D/E), transition to airport-owned for new builds (Terminal F, cargo)."},
]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class Airport5GPipelineOrchestrator:
    """Chains 4 stages: Discover → Diagnose → Negotiate → Stress-Test."""

    def __init__(
        self,
        agents: list[dict[str, str]],
        *,
        thinking_model: str = "claude-opus-4-6",
        orchestration_model: str = "claude-haiku-4-5-20251001",
        thinking_budget: int = 10_000,
        negotiation_rounds: int = 3,
        trace: bool = False,
        trace_path: str | None = None,
    ) -> None:
        self.agents = agents
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.negotiation_rounds = negotiation_rounds
        self.client = make_client(
            protocol_id="airport_5g_pipeline",
            trace=trace,
            trace_path=Path(trace_path) if trace_path else None,
        )

    async def run(self, question: str) -> PipelineResult:
        """Execute the full 4-stage pipeline."""
        t0 = time.time()
        result = PipelineResult(question=question)

        # Stage 1: Discover (1-2-4-All)
        print("\n" + "=" * 70)
        print("STAGE 1: DISCOVER (1-2-4-All)")
        print("=" * 70)
        stage1 = await self._stage1_discover(question)
        result.stages.append(stage1)
        print(f"  Stage 1 complete ({stage1.elapsed_seconds:.1f}s)")

        # Stage 2: Diagnose (ACH)
        print("\n" + "=" * 70)
        print("STAGE 2: DIAGNOSE (Analysis of Competing Hypotheses)")
        print("=" * 70)
        stage2 = await self._stage2_diagnose(question, stage1.output)
        result.stages.append(stage2)
        print(f"  Stage 2 complete ({stage2.elapsed_seconds:.1f}s)")

        # Stage 3: Negotiate (Constraint Negotiation)
        print("\n" + "=" * 70)
        print("STAGE 3: NEGOTIATE (Constraint Negotiation)")
        print("=" * 70)
        winning = stage2.raw_data.get("winning_hypothesis_label", "Hybrid Co-Investment")
        stage3 = await self._stage3_negotiate(question, stage2.output, winning)
        result.stages.append(stage3)
        print(f"  Stage 3 complete ({stage3.elapsed_seconds:.1f}s)")

        # Stage 4: Stress-Test (Red/Blue/White)
        print("\n" + "=" * 70)
        print("STAGE 4: STRESS-TEST (Red/Blue/White Team)")
        print("=" * 70)
        stage4 = await self._stage4_stress_test(question, stage3.output, stage3.raw_data)
        result.stages.append(stage4)
        print(f"  Stage 4 complete ({stage4.elapsed_seconds:.1f}s)")

        result.final_recommendation = stage4.output
        result.total_elapsed = time.time() - t0

        return result

    # ==================================================================
    # Stage 1: Discover (1-2-4-All)
    # ==================================================================

    async def _stage1_discover(self, question: str) -> StageResult:
        t0 = time.time()

        # Phase 1: Solo ideation (parallel, Opus)
        print("  Phase 1: Individual discovery...")
        solo_tasks = [
            self._call_agent(agent, DISCOVER_SOLO_PROMPT.format(question=question))
            for agent in self.agents
        ]
        solo_texts = await asyncio.gather(*solo_tasks)
        solo_outputs = {a["name"]: t for a, t in zip(self.agents, solo_texts)}

        # Phase 2: Pair merge (parallel, Haiku)
        print("  Phase 2: Pair alignment...")
        pairs = [
            (self.agents[0], self.agents[5]),  # CIO + AT&T (technical alignment)
            (self.agents[1], self.agents[4]),  # CRO + Concessions (revenue alignment)
            (self.agents[2], self.agents[3]),  # Airline + Cargo (operations alignment)
        ]
        pair_tasks = [
            self._merge_pair(question, solo_outputs[a["name"]], solo_outputs[b["name"]])
            for a, b in pairs
        ]
        pair_texts = await asyncio.gather(*pair_tasks)

        # Phase 3: Final synthesis (Opus)
        print("  Phase 3: Full group synthesis...")
        group_block = "\n\n---\n\n".join(
            f"**Pair {i+1} ({pairs[i][0]['name']} + {pairs[i][1]['name']}):**\n{text}"
            for i, text in enumerate(pair_texts)
        )
        synthesis = await self._call_synthesis(
            DISCOVER_SYNTHESIS_PROMPT.format(question=question, group_outputs=group_block)
        )

        return StageResult(
            stage_name="discover",
            output=synthesis,
            raw_data={"solo_outputs": solo_outputs, "pair_outputs": pair_texts},
            elapsed_seconds=time.time() - t0,
        )

    async def _merge_pair(self, question: str, ideas_a: str, ideas_b: str) -> str:
        prompt = DISCOVER_PAIR_MERGE_PROMPT.format(
            question=question, ideas_a=ideas_a, ideas_b=ideas_b,
        )
        resp = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return _extract_text(resp)

    # ==================================================================
    # Stage 2: Diagnose (ACH)
    # ==================================================================

    async def _stage2_diagnose(self, question: str, stage1_output: str) -> StageResult:
        t0 = time.time()

        hypotheses = DEFAULT_HYPOTHESES
        hyp_block = "\n".join(
            f"- {h['id']}: **{h['label']}** — {h['description']}" for h in hypotheses
        )

        # Each agent evaluates evidence for/against each hypothesis
        print("  Evaluating evidence across all constituencies...")
        eval_tasks = [
            self._evaluate_hypotheses(agent, question, stage1_output, hyp_block)
            for agent in self.agents
        ]
        all_evidence = await asyncio.gather(*eval_tasks)

        # Build matrix from all agent evaluations
        matrix: dict[tuple[str, str], list[str]] = {}
        all_evidence_items: list[dict] = []
        seen_descriptions: set[str] = set()

        for agent_evidence in all_evidence:
            for ev in agent_evidence:
                desc = ev.get("description", "").strip().lower()
                if desc not in seen_descriptions:
                    seen_descriptions.add(desc)
                    all_evidence_items.append(ev)
                for score in ev.get("scores", []):
                    key = (ev.get("id", ""), score.get("hypothesis_id", ""))
                    matrix.setdefault(key, []).append(score.get("score", "N"))

        # Aggregate via majority vote
        aggregated: dict[tuple[str, str], str] = {}
        for key, votes in matrix.items():
            aggregated[key] = Counter(votes).most_common(1)[0][0]

        # Count inconsistencies per hypothesis
        inconsistency_counts: dict[str, int] = {}
        for h in hypotheses:
            count = sum(
                1 for (_, hid), score in aggregated.items()
                if hid == h["id"] and score == "I"
            )
            inconsistency_counts[h["id"]] = count

        # Format blocks for synthesis
        matrix_lines = []
        e_ids = list({k[0] for k in aggregated})
        h_ids = [h["id"] for h in hypotheses]
        header = f"{'Evidence':<12} | " + " | ".join(f"{hid:^5}" for hid in h_ids)
        matrix_lines.append(header)
        matrix_lines.append("-" * len(header))
        for eid in sorted(e_ids):
            scores = [aggregated.get((eid, hid), "?") for hid in h_ids]
            matrix_lines.append(f"{eid:<12} | " + " | ".join(f"{s:^5}" for s in scores))
        matrix_block = "\n".join(matrix_lines)

        inconsistency_block = "\n".join(
            f"- {h['id']}: {h['label']} — {inconsistency_counts.get(h['id'], 0)} inconsistencies"
            for h in hypotheses
        )

        # Find most diagnostic evidence
        diagnostic_items = []
        for ev in all_evidence_items[:10]:
            eid = ev.get("id", "")
            scores_for_ev = [aggregated.get((eid, hid), "N") for hid in h_ids]
            unique = len(set(scores_for_ev))
            diagnostic_items.append((ev, unique / max(len(scores_for_ev), 1)))
        diagnostic_items.sort(key=lambda x: x[1], reverse=True)
        diagnostic_block = "\n".join(
            f"- {ev.get('id', '?')}: {ev.get('description', '')} (diagnosticity: {score:.2f})"
            for ev, score in diagnostic_items[:5]
        )

        # Synthesis (Opus)
        print("  Synthesizing ACH results...")
        synthesis_prompt = ACH_SYNTHESIS_PROMPT.format(
            question=question,
            hypotheses_block=hyp_block,
            matrix_block=matrix_block,
            inconsistency_block=inconsistency_block,
            diagnostic_block=diagnostic_block,
        )
        resp = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{"role": "user", "content": synthesis_prompt}],
        )
        synthesis_text = _extract_text(resp)
        synthesis_data = _parse_json(synthesis_text)

        return StageResult(
            stage_name="diagnose",
            output=synthesis_text,
            raw_data={
                **synthesis_data,
                "matrix": {f"{k[0]}|{k[1]}": v for k, v in aggregated.items()},
                "inconsistency_counts": inconsistency_counts,
            },
            elapsed_seconds=time.time() - t0,
        )

    async def _evaluate_hypotheses(
        self, agent: dict, question: str, stage1_output: str, hypotheses_block: str,
    ) -> list[dict]:
        prompt = ACH_HYPOTHESIS_PROMPT.format(
            question=question,
            agent_name=agent["name"],
            system_prompt=agent.get("system_prompt", ""),
            stage1_output=stage1_output,
            hypotheses_block=hypotheses_block,
        )
        resp = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            system=agent.get("system_prompt", ""),
            messages=[{"role": "user", "content": prompt}],
        )
        parsed = _parse_json(_extract_text(resp))
        return parsed.get("evidence", [])

    # ==================================================================
    # Stage 3: Negotiate (Constraint Negotiation)
    # ==================================================================

    async def _stage3_negotiate(
        self, question: str, stage2_output: str, winning_hypothesis: str,
    ) -> StageResult:
        t0 = time.time()
        constraint_store = ConstraintStore()
        extractor = ConstraintExtractor(model=self.orchestration_model)
        rounds_data: list[dict] = []

        for round_num in range(1, self.negotiation_rounds + 1):
            if round_num == 1:
                print(f"  Round {round_num}/{self.negotiation_rounds}: Opening positions...")
                tasks = [
                    self._negotiate_opening(agent, question, winning_hypothesis, stage2_output)
                    for agent in self.agents
                ]
            else:
                print(f"  Round {round_num}/{self.negotiation_rounds}: Revisions...")
                peer_constraints = constraint_store.format_for_prompt()
                prior_args = "\n\n".join(
                    f"[{a['name']}]:\n{a['content']}"
                    for rnd in rounds_data
                    for a in rnd["arguments"]
                )
                tasks = [
                    self._negotiate_revision(
                        agent, question, winning_hypothesis, round_num,
                        constraint_store.format_for_prompt(exclude_role=agent["name"]),
                        prior_args,
                    )
                    for agent in self.agents
                ]

            texts = await asyncio.gather(*tasks)
            arguments = [
                {"name": a["name"], "content": t, "round": round_num}
                for a, t in zip(self.agents, texts)
            ]
            rounds_data.append({"round": round_num, "arguments": arguments})

            # Extract constraints (gracefully handle parse failures)
            print("  Extracting constraints...")
            for arg in arguments:
                try:
                    constraints = await extractor.extract(arg["name"], arg["content"])
                    constraint_store.add_many(constraints)
                except Exception as e:
                    print(f"    Warning: constraint extraction failed for {arg['name']}: {e}")

        # Synthesis
        print("  Synthesizing negotiation outcome...")
        transcript = "\n\n".join(
            f"--- Round {rnd['round']} ---\n" + "\n\n".join(
                f"[{a['name']}]:\n{a['content']}" for a in rnd["arguments"]
            )
            for rnd in rounds_data
        )
        synthesis_prompt = NEGOTIATE_SYNTHESIS_PROMPT.format(
            winning_hypothesis=winning_hypothesis,
            question=question,
            constraint_table=constraint_store.format_for_prompt(),
            transcript=transcript,
        )
        resp = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            system="You are a strategic synthesizer producing actionable conclusions from multi-stakeholder constraint negotiations.",
            messages=[{"role": "user", "content": synthesis_prompt}],
        )
        synthesis_text = _extract_text(resp)

        return StageResult(
            stage_name="negotiate",
            output=synthesis_text,
            raw_data={
                "constraint_table": constraint_store.format_for_prompt(),
                "rounds": rounds_data,
                "winning_hypothesis": winning_hypothesis,
            },
            elapsed_seconds=time.time() - t0,
        )

    async def _negotiate_opening(
        self, agent: dict, question: str, winning_hypothesis: str, stage2_output: str,
    ) -> str:
        prompt = NEGOTIATE_OPENING_PROMPT.format(
            winning_hypothesis=winning_hypothesis,
            stage2_output=stage2_output,
            question=question,
        )
        resp = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            system=agent.get("system_prompt", ""),
            messages=[{"role": "user", "content": prompt}],
        )
        return _extract_text(resp)

    async def _negotiate_revision(
        self, agent: dict, question: str, winning_hypothesis: str,
        round_number: int, peer_constraints: str, prior_arguments: str,
    ) -> str:
        prompt = NEGOTIATE_REVISION_PROMPT.format(
            winning_hypothesis=winning_hypothesis,
            question=question,
            round_number=round_number,
            peer_constraints=peer_constraints,
            prior_arguments=prior_arguments,
        )
        resp = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            system=agent.get("system_prompt", ""),
            messages=[{"role": "user", "content": prompt}],
        )
        return _extract_text(resp)

    # ==================================================================
    # Stage 4: Stress-Test (Red/Blue/White)
    # ==================================================================

    async def _stage4_stress_test(
        self, question: str, consensus: str, stage3_data: dict,
    ) -> StageResult:
        t0 = time.time()

        # Dynamic team assignment
        print("  Assigning Red/Blue/White teams...")
        teams = await assign_teams(
            agents=self.agents,
            constraint_table=stage3_data.get("constraint_table", ""),
            negotiation_synthesis=consensus,
            model=self.orchestration_model,
        )

        red_agents = teams["red_team"]
        blue_agents = teams["blue_team"]
        white_agents = teams["white_team"]

        red_names = [a["name"] for a in red_agents]
        blue_names = [a["name"] for a in blue_agents]
        white_names = [a["name"] for a in white_agents]
        print(f"  Red Team: {', '.join(red_names)}")
        print(f"  Blue Team: {', '.join(blue_names)}")
        print(f"  White Team: {', '.join(white_names)}")

        # Phase 1: Red Team Attack
        print("  Red Team attacking...")
        attack_tasks = [
            self._red_attack(agent, question, consensus)
            for agent in red_agents
        ]
        attacks_raw = await asyncio.gather(*attack_tasks)
        attacks = []
        for agent, raw in zip(red_agents, attacks_raw):
            parsed = _parse_json(raw)
            attacks.append({
                "agent": agent["name"],
                "vulnerabilities": parsed.get("vulnerabilities", []),
            })

        attacks_block = _format_attacks_block(attacks)

        # Phase 2: Blue Team Defense
        print("  Blue Team defending...")
        defense_tasks = [
            self._blue_defense(agent, question, consensus, attacks_block)
            for agent in blue_agents
        ]
        defenses_raw = await asyncio.gather(*defense_tasks)
        defenses = []
        for agent, raw in zip(blue_agents, defenses_raw):
            parsed = _parse_json(raw)
            defenses.append({
                "agent": agent["name"],
                "mitigations": parsed.get("mitigations", []),
            })

        defenses_block = _format_defenses_block(defenses)

        # Phase 3: White Team Adjudication
        print("  White Team adjudicating...")
        white_agent = white_agents[0] if white_agents else self.agents[0]
        adjudication_text = await self._white_adjudicate(
            white_agent, question, consensus, attacks_block, defenses_block,
        )
        adjudication = _parse_json(adjudication_text)

        # Format final output
        final_output = self._format_final_output(
            attacks, defenses, adjudication, teams.get("reasoning", {}),
        )

        return StageResult(
            stage_name="stress_test",
            output=final_output,
            raw_data={
                "teams": {
                    "red": red_names,
                    "blue": blue_names,
                    "white": white_names,
                    "reasoning": teams.get("reasoning", {}),
                },
                "attacks": attacks,
                "defenses": defenses,
                "adjudication": adjudication,
            },
            elapsed_seconds=time.time() - t0,
        )

    async def _red_attack(self, agent: dict, question: str, consensus: str) -> str:
        prompt = STRESS_RED_PROMPT.format(
            agent_name=agent["name"],
            system_prompt=agent.get("system_prompt", ""),
            question=question,
            consensus=consensus,
        )
        resp = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{"role": "user", "content": prompt}],
        )
        return _extract_text(resp)

    async def _blue_defense(
        self, agent: dict, question: str, consensus: str, attacks_block: str,
    ) -> str:
        prompt = STRESS_BLUE_PROMPT.format(
            agent_name=agent["name"],
            system_prompt=agent.get("system_prompt", ""),
            question=question,
            consensus=consensus,
            attacks_block=attacks_block,
        )
        resp = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{"role": "user", "content": prompt}],
        )
        return _extract_text(resp)

    async def _white_adjudicate(
        self, agent: dict, question: str, consensus: str,
        attacks_block: str, defenses_block: str,
    ) -> str:
        prompt = STRESS_WHITE_PROMPT.format(
            question=question,
            consensus=consensus,
            attacks_block=attacks_block,
            defenses_block=defenses_block,
        )
        resp = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 8192,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            system=agent.get("system_prompt", ""),
            messages=[{"role": "user", "content": prompt}],
        )
        return _extract_text(resp)

    # ==================================================================
    # Helpers
    # ==================================================================

    async def _call_agent(self, agent: dict, prompt: str) -> str:
        """Call a single agent with their system prompt (Opus + thinking)."""
        resp = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            system=agent.get("system_prompt", ""),
            messages=[{"role": "user", "content": prompt}],
        )
        return _extract_text(resp)

    async def _call_synthesis(self, prompt: str) -> str:
        """Call synthesis with Opus + thinking (no agent system prompt)."""
        resp = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 8192,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            messages=[{"role": "user", "content": prompt}],
        )
        return _extract_text(resp)

    @staticmethod
    def _format_final_output(
        attacks: list[dict], defenses: list[dict],
        adjudication: dict, team_reasoning: dict,
    ) -> str:
        """Format the Stage 4 output as readable text."""
        sections = []

        # Team assignments
        sections.append("## Team Assignment Reasoning")
        for key in ["red_rationale", "blue_rationale", "white_rationale"]:
            if key in team_reasoning:
                sections.append(f"- **{key.replace('_', ' ').title()}**: {team_reasoning[key]}")

        # Attacks
        sections.append("\n## Red Team Attacks")
        for attack in attacks:
            sections.append(f"\n### {attack['agent']}")
            for v in attack.get("vulnerabilities", []):
                sections.append(
                    f"- **[{v.get('id', '?')}] {v.get('title', '')}** "
                    f"({v.get('severity', '?')}): {v.get('description', '')}"
                )

        # Defenses
        sections.append("\n## Blue Team Defenses")
        for defense in defenses:
            sections.append(f"\n### {defense['agent']}")
            for m in defense.get("mitigations", []):
                sections.append(
                    f"- **{m.get('vulnerability_id', '?')}** "
                    f"({m.get('defense_type', '?')}): {m.get('response', '')}"
                )

        # Adjudication
        sections.append("\n## White Team Adjudication")
        for adj in adjudication.get("adjudications", []):
            sections.append(
                f"- **[{adj.get('vulnerability_id', '?')}] {adj.get('vulnerability_title', '')}**: "
                f"{adj.get('verdict', '?')} — {adj.get('reasoning', '')}"
            )

        # Final recommendation
        final = adjudication.get("final_recommendation", {})
        if final:
            sections.append("\n## Board-Ready Recommendation")
            sections.append(f"**Plan Strength Score**: {final.get('plan_strength_score', 'N/A')}/10")
            sections.append(f"**Go/No-Go**: {final.get('go_no_go', 'N/A')}")
            conditions = final.get("conditions", [])
            if conditions:
                sections.append("**Conditions:**")
                for c in conditions:
                    sections.append(f"  - {c}")
            narrative = final.get("board_narrative", "")
            if narrative:
                sections.append(f"\n{narrative}")

        return "\n".join(sections)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _extract_text(response: anthropic.types.Message) -> str:
    parts = []
    for block in response.content:
        if hasattr(block, "text"):
            parts.append(block.text)
    return "\n".join(parts)


def _parse_json(text: str) -> dict:
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


def _format_attacks_block(attacks: list[dict]) -> str:
    lines = []
    for attack in attacks:
        for v in attack.get("vulnerabilities", []):
            lines.append(
                f"[{v.get('id', '?')}] ({v.get('severity', '?')}) "
                f"{v.get('title', 'untitled')} — from {attack['agent']}\n"
                f"  Description: {v.get('description', '')}\n"
                f"  Failure scenario: {v.get('failure_scenario', '')}"
            )
    return "\n\n".join(lines) if lines else "No attacks identified."


def _format_defenses_block(defenses: list[dict]) -> str:
    lines = []
    for defense in defenses:
        for m in defense.get("mitigations", []):
            lines.append(
                f"Defense for {m.get('vulnerability_id', '?')} "
                f"({m.get('defense_type', '?')}) — from {defense['agent']}\n"
                f"  Response: {m.get('response', '')}\n"
                f"  Evidence: {m.get('evidence', '')}\n"
                f"  Residual risk: {m.get('residual_risk', '')}"
            )
    return "\n\n".join(lines) if lines else "No defenses provided."
