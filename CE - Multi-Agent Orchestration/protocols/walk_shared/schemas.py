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
    distinctiveness: float = Field(default=5.0, ge=1, le=10)
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


# ── Stage 4.5: Collision Synthesis ──────────────────────────────────────────

class CollisionFusion(BaseModel):
    """One generative collision between two lenses producing an emergent idea.

    Unlike CrossExamEntry (adversarial), this captures A + B → C fusion —
    a third idea neither lens stated that dissolves a Frame tension.
    """

    lens_a_key: str
    lens_b_key: str
    pairing_type: str  # "core-core" | "core-periphery" | "periphery-periphery"
    collision_insight: str
    emergent_idea: str
    frame_tension_resolved: str = ""
    surprise_score: float = Field(ge=1, le=10)
    resolution_power: float = Field(ge=1, le=10)
    composite: float = 0.0


# ── Stage 5: Synthesis ──────────────────────────────────────────────────────

class WalkSynthesis(BaseModel):
    """Structured synthesis integrating all walk stages."""

    strongest_unresolved_tension: str
    competing_interpretations: list[str]
    minority_report: str
    action_divergence: list[str]
    redundancy_assessment: str
    walk_added_value: str
    decision_changes: list[str]
    experiments: list[str]
    success_signals: list[str]
    kill_criteria: list[str]
    what_would_change_view: str


# ── Stage 6: Provocation (walk-back-to-desk bridge) ─────────────────────────

class WalkProvocation(BaseModel):
    """The walk-back-to-desk artifact. NOT a summary. A provocation.

    Designed to keep the walk's energy alive long enough for the walker to
    write at the desk. Pulls verbatim sharpest statements, names contradictions
    between them, and identifies the one thread with highest latent energy
    that the walk abandoned.
    """

    sharpest_statements: list[str]
    statement_sources: list[str]
    contradictions: list[str]
    underdeveloped_thread: str
    why_underdeveloped: str
    follow_up_prompt: str


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
    collisions: list[CollisionFusion] = []
    synthesis: WalkSynthesis | None = None
    synthesis_text: str = ""
    provocation: WalkProvocation | None = None
