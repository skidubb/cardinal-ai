"""Tests for walk_shared.schemas — Pydantic models for all Walk protocol stages."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


# ── FrameArtifact ────────────────────────────────────────────────────────────

class TestFrameArtifact:
    def test_happy_path(self):
        from protocols.walk_shared.schemas import FrameArtifact
        fa = FrameArtifact(
            question="Should we build an AI lab?",
            objective="Decide build vs partner for AI capability",
            constraints=["burn rate frozen", "18-month runway"],
            assumptions=["AI features are table stakes"],
            known_dead_ends=["acqui-hire failed last year"],
            ambiguity_map=["definition of 'AI lab' unclear"],
            unresolved_tensions=["CEO wants speed, CFO wants cost control"],
        )
        assert fa.question == "Should we build an AI lab?"
        assert len(fa.constraints) == 2
        assert len(fa.unresolved_tensions) == 1

    def test_empty_optional_lists(self):
        from protocols.walk_shared.schemas import FrameArtifact
        fa = FrameArtifact(
            question="Q",
            objective="O",
            constraints=[],
            assumptions=[],
            known_dead_ends=[],
            ambiguity_map=[],
            unresolved_tensions=[],
        )
        assert fa.known_dead_ends == []

    def test_serialization_roundtrip(self):
        from protocols.walk_shared.schemas import FrameArtifact
        fa = FrameArtifact(
            question="Q", objective="O", constraints=["c1"],
            assumptions=["a1"], known_dead_ends=[], ambiguity_map=[],
            unresolved_tensions=["t1"],
        )
        data = fa.model_dump()
        fa2 = FrameArtifact.model_validate(data)
        assert fa == fa2


# ── ShallowWalkOutput ────────────────────────────────────────────────────────

class TestShallowWalkOutput:
    def test_happy_path(self):
        from protocols.walk_shared.schemas import ShallowWalkOutput
        s = ShallowWalkOutput(
            agent_key="walk-systems",
            agent_name="Systems Walker",
            lens_family="systems",
            reframe="The problem is a feedback loop, not a decision.",
            hidden_variable="employee morale",
            blind_spot="ignoring second-order effects",
            testable_implication="If morale drops >10%, attrition doubles.",
        )
        assert s.agent_key == "walk-systems"
        assert s.lens_family == "systems"

    def test_missing_required_field(self):
        from protocols.walk_shared.schemas import ShallowWalkOutput
        with pytest.raises(ValidationError):
            ShallowWalkOutput(
                agent_key="walk-systems",
                # missing agent_name, lens_family, etc.
            )


# ── SalienceScore ────────────────────────────────────────────────────────────

class TestSalienceScore:
    def test_valid_scores(self):
        from protocols.walk_shared.schemas import SalienceScore
        s = SalienceScore(
            agent_key="walk-poet",
            novelty=8.5, explanatory_power=7.0,
            actionability=6.0, cognitive_distance=9.0,
            composite=7.6, rationale="Metaphor reveals hidden structure",
        )
        assert s.novelty == 8.5
        assert s.composite == 7.6

    def test_score_below_minimum(self):
        from protocols.walk_shared.schemas import SalienceScore
        with pytest.raises(ValidationError):
            SalienceScore(
                agent_key="x", novelty=0.5, explanatory_power=1.0,
                actionability=1.0, cognitive_distance=1.0,
                composite=1.0, rationale="r",
            )

    def test_score_above_maximum(self):
        from protocols.walk_shared.schemas import SalienceScore
        with pytest.raises(ValidationError):
            SalienceScore(
                agent_key="x", novelty=11.0, explanatory_power=1.0,
                actionability=1.0, cognitive_distance=1.0,
                composite=1.0, rationale="r",
            )


# ── SalienceArtifact ─────────────────────────────────────────────────────────

class TestSalienceArtifact:
    def test_with_wildcard(self):
        from protocols.walk_shared.schemas import SalienceScore, SalienceArtifact
        score = SalienceScore(
            agent_key="walk-poet", novelty=9.0, explanatory_power=6.0,
            actionability=5.0, cognitive_distance=9.5,
            composite=7.4, rationale="r",
        )
        sa = SalienceArtifact(
            ranked_outputs=[score],
            top_tensions=["t1"],
            candidate_hypotheses=["h1"],
            promoted_agents=["walk-poet"],
            wildcard_agent="walk-semiotician",
            wildcard_rationale="Maximally orthogonal to top lens",
        )
        assert sa.wildcard_agent == "walk-semiotician"

    def test_without_wildcard(self):
        from protocols.walk_shared.schemas import SalienceArtifact
        sa = SalienceArtifact(
            ranked_outputs=[], top_tensions=[], candidate_hypotheses=[],
            promoted_agents=["walk-systems"],
        )
        assert sa.wildcard_agent is None


# ── DeepWalkOutput ───────────────────────────────────────────────────────────

class TestDeepWalkOutput:
    def test_happy_path(self):
        from protocols.walk_shared.schemas import DeepWalkOutput
        d = DeepWalkOutput(
            agent_key="walk-systems",
            agent_name="Systems Walker",
            thesis="The core dynamic is a reinforcing loop.",
            critique_of_incumbent_frame="Ignores feedback effects.",
            critique_of_other_lens="Analogy walker's parallel is surface-level.",
            decision_implication="Intervene at the delay, not the symptom.",
            disconfirming_evidence="If no feedback loop exists, metrics diverge.",
            priority_test="Measure lag between intervention and outcome.",
        )
        assert d.thesis.startswith("The core")


# ── CrossExamEntry ───────────────────────────────────────────────────────────

class TestCrossExamEntry:
    def test_happy_path(self):
        from protocols.walk_shared.schemas import CrossExamEntry
        c = CrossExamEntry(
            challenger_key="walk-adversarial",
            target_key="walk-systems",
            strongest_opposing_claim="No empirical evidence for the feedback loop.",
            settling_evidence="Time-series data showing lag correlation.",
            concession="The feedback loop hypothesis is plausible but unproven.",
        )
        assert c.challenger_key == "walk-adversarial"


# ── WalkSynthesis ────────────────────────────────────────────────────────────

class TestWalkSynthesis:
    def test_happy_path(self):
        from protocols.walk_shared.schemas import WalkSynthesis
        ws = WalkSynthesis(
            best_current_interpretation="The problem is a systems trap.",
            competing_interpretations=["Narrative: it's a hero's journey gone wrong"],
            walk_added_value="Surfaced feedback loop invisible to expert stack.",
            decision_changes=["Shift from symptom treatment to delay reduction"],
            experiments=["Measure lag time between action and outcome"],
            success_signals=["Lag decreases below 2 weeks"],
            kill_criteria=["No measurable feedback loop after 3 months of data"],
            what_would_change_view="Evidence that the system is linear, not looped.",
        )
        assert len(ws.experiments) == 1
        assert len(ws.kill_criteria) == 1


# ── WalkResult ───────────────────────────────────────────────────────────────

class TestWalkResult:
    def test_minimal_result(self):
        from protocols.walk_shared.schemas import (
            WalkResult, FrameArtifact, SalienceArtifact, WalkSynthesis,
        )
        frame = FrameArtifact(
            question="Q", objective="O", constraints=[], assumptions=[],
            known_dead_ends=[], ambiguity_map=[], unresolved_tensions=[],
        )
        salience = SalienceArtifact(
            ranked_outputs=[], top_tensions=[], candidate_hypotheses=[],
            promoted_agents=[],
        )
        result = WalkResult(
            question="Q",
            protocol_variant="walk_base",
            frame=frame,
            shallow_outputs=[],
            salience=salience,
            deep_outputs=[],
            cross_exam=[],
        )
        assert result.synthesis is None
        assert result.synthesis_text == ""

    def test_full_roundtrip(self):
        from protocols.walk_shared.schemas import (
            WalkResult, FrameArtifact, SalienceArtifact, WalkSynthesis,
            ShallowWalkOutput, SalienceScore, DeepWalkOutput, CrossExamEntry,
        )
        frame = FrameArtifact(
            question="Q", objective="O", constraints=["c"], assumptions=["a"],
            known_dead_ends=[], ambiguity_map=["am"], unresolved_tensions=["t"],
        )
        shallow = ShallowWalkOutput(
            agent_key="walk-systems", agent_name="Systems Walker",
            lens_family="systems", reframe="r", hidden_variable="h",
            blind_spot="b", testable_implication="t",
        )
        score = SalienceScore(
            agent_key="walk-systems", novelty=8.0, explanatory_power=7.0,
            actionability=6.0, cognitive_distance=5.0, composite=6.5, rationale="r",
        )
        salience = SalienceArtifact(
            ranked_outputs=[score], top_tensions=["t"],
            candidate_hypotheses=["h"], promoted_agents=["walk-systems"],
        )
        deep = DeepWalkOutput(
            agent_key="walk-systems", agent_name="Systems Walker",
            thesis="th", critique_of_incumbent_frame="c",
            critique_of_other_lens="c2", decision_implication="d",
            disconfirming_evidence="de", priority_test="pt",
        )
        cross = CrossExamEntry(
            challenger_key="walk-adversarial", target_key="walk-systems",
            strongest_opposing_claim="soc", settling_evidence="se",
            concession="con",
        )
        synth = WalkSynthesis(
            best_current_interpretation="bci",
            competing_interpretations=["ci"],
            walk_added_value="wav",
            decision_changes=["dc"],
            experiments=["e"],
            success_signals=["ss"],
            kill_criteria=["kc"],
            what_would_change_view="wwcv",
        )
        result = WalkResult(
            question="Q", protocol_variant="walk_base",
            frame=frame, shallow_outputs=[shallow], salience=salience,
            deep_outputs=[deep], cross_exam=[cross], synthesis=synth,
            synthesis_text="Full prose synthesis here.",
        )
        data = result.model_dump()
        result2 = WalkResult.model_validate(data)
        assert result2.protocol_variant == "walk_base"
        assert len(result2.shallow_outputs) == 1
        assert result2.synthesis is not None
