"""Tests for P49 Walk Base orchestrator — mocked LLM calls."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest


def _make_mock_response(text: str):
    """Build a minimal mock Anthropic response."""
    tb = type("TextBlock", (), {"type": "text", "text": text})()
    resp = MagicMock()
    resp.content = [tb]
    resp.usage = type("U", (), {
        "input_tokens": 100, "output_tokens": 50,
        "cache_read_input_tokens": 0,
    })()
    return resp


def _frame_json():
    return json.dumps({
        "question": "Q", "objective": "O",
        "constraints": ["c1"], "assumptions": ["a1"],
        "known_dead_ends": [], "ambiguity_map": ["am"],
        "unresolved_tensions": ["t1"],
    })


def _shallow_json(agent_key: str):
    return json.dumps({
        "agent_key": agent_key, "agent_name": f"Agent {agent_key}",
        "lens_family": "systems", "reframe": "r",
        "hidden_variable": "h", "blind_spot": "b",
        "testable_implication": "t",
    })


def _salience_json(agent_keys: list[str]):
    scores = []
    for i, key in enumerate(agent_keys):
        scores.append({
            "agent_key": key, "novelty": 8.0 - i, "explanatory_power": 7.0,
            "actionability": 6.0, "cognitive_distance": 5.0 + i,
            "composite": 7.0 - i * 0.5, "rationale": "test",
        })
    return json.dumps({
        "ranked_outputs": scores,
        "top_tensions": ["t1"],
        "candidate_hypotheses": ["h1"],
        "promoted_agents": agent_keys[:3],
    })


def _deep_json(agent_key: str):
    return json.dumps({
        "agent_key": agent_key, "agent_name": f"Agent {agent_key}",
        "thesis": "th", "critique_of_incumbent_frame": "cif",
        "critique_of_other_lens": "col",
        "decision_implication": "di",
        "disconfirming_evidence": "de", "priority_test": "pt",
    })


def _cross_exam_json(challenger: str, target: str):
    return json.dumps({
        "challenger_key": challenger, "target_key": target,
        "strongest_opposing_claim": "soc",
        "settling_evidence": "se", "concession": "con",
    })


def _synthesis_json():
    return json.dumps({
        "best_current_interpretation": "bci",
        "competing_interpretations": ["ci1"],
        "walk_added_value": "wav",
        "decision_changes": ["dc1"],
        "experiments": ["e1"],
        "success_signals": ["ss1"],
        "kill_criteria": ["kc1"],
        "what_would_change_view": "wwcv",
    })


class TestWalkBaseOrchestrator:
    """Test the full 6-stage pipeline with mocked LLM calls."""

    @patch("protocols.walk_shared.agents.WALK_AGENTS")
    def test_orchestrator_init(self, _):
        from protocols.p49_walk_base.orchestrator import WalkBaseOrchestrator
        agents = [{"name": "Test", "system_prompt": "test"}]
        orch = WalkBaseOrchestrator(
            agents=agents,
            thinking_model="claude-opus-4-6",
            orchestration_model="claude-haiku-4-5-20251001",
        )
        assert orch is not None

    def test_orchestrator_requires_agents(self):
        from protocols.p49_walk_base.orchestrator import WalkBaseOrchestrator
        with pytest.raises(ValueError):
            WalkBaseOrchestrator(agents=[])

    @patch("protocols.langfuse_tracing.create_span", return_value=None)
    @patch("protocols.langfuse_tracing.end_span")
    @patch("protocols.langfuse_tracing._langfuse_available", False)
    def test_full_pipeline_mocked(self, mock_end_span, mock_create_span):
        """End-to-end pipeline with mocked LLM returning valid JSON."""
        from protocols.p49_walk_base.orchestrator import WalkBaseOrchestrator
        from protocols.walk_shared.agents import WALK_AGENTS

        walk_agent_list = [
            {**v, "_key": k} for k, v in list(WALK_AGENTS.items())[:6]
        ]
        walker_keys = [a["_key"] for a in walk_agent_list
                       if a.get("walk_metadata", {}).get("default_depth_mode") not in ("frame", "score", "synthesize")]

        orch = WalkBaseOrchestrator(
            agents=walk_agent_list,
            thinking_model="claude-opus-4-6",
            orchestration_model="claude-haiku-4-5-20251001",
            thinking_budget=10000,
            promote_count=2,
        )

        # Build a call counter to return different responses per stage
        call_count = {"n": 0}
        stage_responses = []

        # Stage 0: Frame
        stage_responses.append(_frame_json())
        # Stage 1: Shallow walks (one per walker)
        for key in walker_keys:
            stage_responses.append(_shallow_json(key))
        # Stage 2: Salience
        stage_responses.append(_salience_json(walker_keys))
        # Stage 3: Deep walks (for promoted agents)
        for key in walker_keys[:2]:
            stage_responses.append(_deep_json(key))
        # Stage 4: Cross-exam
        stage_responses.append(_cross_exam_json(walker_keys[0], walker_keys[1]))
        stage_responses.append(_cross_exam_json(walker_keys[1], walker_keys[0]))
        # Stage 5: Synthesis (via SynthesisEngine.synthesize → agent_complete)
        synth_text = _synthesis_json() + "\n---PROSE---\nFull prose synthesis output here."
        stage_responses.append(synth_text)

        async def mock_agent_complete(agent, fallback_model, messages, thinking_budget=None, anthropic_client=None, **kw):
            idx = call_count["n"]
            call_count["n"] += 1
            if idx < len(stage_responses):
                return stage_responses[idx]
            return "{}"

        async def mock_llm_complete(client, model, messages, agent_name=None, max_tokens=None, **kw):
            idx = call_count["n"]
            call_count["n"] += 1
            text = stage_responses[idx] if idx < len(stage_responses) else "{}"
            return _make_mock_response(text)

        with patch("protocols.p49_walk_base.orchestrator.agent_complete", side_effect=mock_agent_complete), \
             patch("protocols.p49_walk_base.orchestrator.llm_complete", side_effect=mock_llm_complete), \
             patch("protocols.walk_shared.selection.llm_complete", side_effect=mock_llm_complete), \
             patch("protocols.walk_shared.selection.extract_text", side_effect=lambda r: r.content[0].text if hasattr(r, 'content') else str(r)), \
             patch("protocols.llm.agent_complete", side_effect=mock_agent_complete), \
             patch("protocols.p49_walk_base.orchestrator.make_client", return_value=AsyncMock()):

            result = asyncio.run(orch.run("Should we build an AI lab?"))

        from protocols.walk_shared.schemas import WalkResult
        assert isinstance(result, WalkResult)
        assert result.question == "Should we build an AI lab?"
        assert result.protocol_variant == "walk_base"
        assert result.frame is not None
        assert len(result.shallow_outputs) > 0


class TestWalkBaseRunCLI:
    """Test the CLI module can be imported and has expected structure."""

    def test_run_module_importable(self):
        from protocols.p49_walk_base import run
        assert hasattr(run, "main")
        assert hasattr(run, "print_result")


class TestVariantOrchestrators:
    """Test that variant orchestrator classes exist and inherit correctly."""

    def test_tournament_walk_importable(self):
        from protocols.p50_tournament_walk.orchestrator import TournamentWalkOrchestrator
        assert hasattr(TournamentWalkOrchestrator, "run")

    def test_wildcard_walk_importable(self):
        from protocols.p51_wildcard_walk.orchestrator import WildcardWalkOrchestrator
        assert hasattr(WildcardWalkOrchestrator, "run")

    def test_drift_return_walk_importable(self):
        from protocols.p52_drift_return_walk.orchestrator import DriftReturnWalkOrchestrator
        assert hasattr(DriftReturnWalkOrchestrator, "run")

    def test_tournament_has_no_cross_exam(self):
        """P50 Tournament should not have a _cross_examine method."""
        from protocols.p50_tournament_walk.orchestrator import TournamentWalkOrchestrator
        assert not hasattr(TournamentWalkOrchestrator, "_cross_examine")

    def test_wildcard_uses_wildcard_flag(self):
        from protocols.p51_wildcard_walk.orchestrator import WildcardWalkOrchestrator
        orch = WildcardWalkOrchestrator(
            agents=[{"name": "T", "system_prompt": "t"}],
        )
        assert orch.include_wildcard is True

    def test_drift_return_variant_name(self):
        from protocols.p52_drift_return_walk.orchestrator import DriftReturnWalkOrchestrator
        orch = DriftReturnWalkOrchestrator(
            agents=[{"name": "T", "system_prompt": "t"}],
        )
        assert orch.variant_name == "drift_return"


class TestConfigIntegration:
    """Test walk stages are registered in config."""

    def test_walk_stages_in_cognitive_map(self):
        from protocols.config import STAGE_COGNITIVE_MAP
        assert STAGE_COGNITIVE_MAP.get("frame") == "L4"
        assert STAGE_COGNITIVE_MAP.get("shallow_walk") == "L3"
        assert STAGE_COGNITIVE_MAP.get("salience") == "L2"
        assert STAGE_COGNITIVE_MAP.get("deep_walk") == "L4"
        assert STAGE_COGNITIVE_MAP.get("cross_exam") == "L3"
