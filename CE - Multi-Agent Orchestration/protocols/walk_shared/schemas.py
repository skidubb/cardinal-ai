"""Pydantic v2 models for all Walk protocol stage artifacts.

These are the data contract for the Walk protocol family (P49-P52).
All inter-stage communication is JSON-first via these models.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Stage 0: Frame ───────────────────────────────────────────────────────────

class FrameArtifact(BaseModel):
    """Structured problem decomposition produced by the Problem Framer."""

    question: str
    objective: str
    constraints: list[str]
    assumptions: list[str]
    known_dead_ends: list[str]
    ambiguity_map: list[str]
    unresolved_tensions: list[str]


# ── Stage 1: Shallow Walk ────────────────────────────────────────────────────

class ShallowWalkOutput(BaseModel):
    """One reframing from a single cognitive lens."""

    agent_key: str
    agent_name: str
    lens_family: str
    reframe: str
    hidden_variable: str
    blind_spot: str
    testable_implication: str


# ── Stage 2: Salience ───────────────────────────────────────────────────────

class SalienceScore(BaseModel):
    """Salience Judge's score for one shallow output."""

    agent_key: str
    novelty: float = Field(ge=1, le=10)
    explanatory_power: float = Field(ge=1, le=10)
    actionability: float = Field(ge=1, le=10)
    cognitive_distance: float = Field(ge=1, le=10)
    composite: float
    rationale: str


class SalienceArtifact(BaseModel):
    """Aggregate salience scoring result with promotion decisions."""

    ranked_outputs: list[SalienceScore]
    top_tensions: list[str]
    candidate_hypotheses: list[str]
    promoted_agents: list[str]
    wildcard_agent: str | None = None
    wildcard_rationale: str | None = None


# ── Stage 3: Deep Walk ──────────────────────────────────────────────────────

class DeepWalkOutput(BaseModel):
    """Deep analysis from a promoted cognitive lens."""

    agent_key: str
    agent_name: str
    thesis: str
    critique_of_incumbent_frame: str
    critique_of_other_lens: str
    decision_implication: str
    disconfirming_evidence: str
    priority_test: str


# ── Stage 4: Cross-Examination ──────────────────────────────────────────────

class CrossExamEntry(BaseModel):
    """One directed cross-examination between promoted lenses."""

    challenger_key: str
    target_key: str
    strongest_opposing_claim: str
    settling_evidence: str
    concession: str


# ── Stage 5: Synthesis ──────────────────────────────────────────────────────

class WalkSynthesis(BaseModel):
    """Structured synthesis integrating all walk stages."""

    best_current_interpretation: str
    competing_interpretations: list[str]
    walk_added_value: str
    decision_changes: list[str]
    experiments: list[str]
    success_signals: list[str]
    kill_criteria: list[str]
    what_would_change_view: str


# ── Full Result ─────────────────────────────────────────────────────────────

class WalkResult(BaseModel):
    """Complete output of any Walk protocol variant."""

    question: str
    protocol_variant: str
    frame: FrameArtifact
    shallow_outputs: list[ShallowWalkOutput]
    salience: SalienceArtifact
    deep_outputs: list[DeepWalkOutput]
    cross_exam: list[CrossExamEntry]
    synthesis: WalkSynthesis | None = None
    synthesis_text: str = ""
