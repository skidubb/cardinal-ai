"""Tests for walk_shared.agents — Walk-specific agent definitions."""

from __future__ import annotations

import pytest


EXPECTED_CORE_WALKERS = {
    "walk-framer", "walk-systems", "walk-analogy", "walk-narrative",
    "walk-constraint", "walk-adversarial", "walk-salience-judge",
    "walk-synthesizer",
}

EXPECTED_DISTANT_SPECIALISTS = {
    "walk-poet", "walk-historian", "walk-complexity",
    "walk-semiotician", "walk-economist", "walk-statistician",
}

ALL_WALK_KEYS = EXPECTED_CORE_WALKERS | EXPECTED_DISTANT_SPECIALISTS


class TestWalkAgentDefinitions:
    def test_all_14_agents_defined(self):
        from protocols.walk_shared.agents import WALK_AGENTS
        assert len(WALK_AGENTS) == 14

    def test_core_walkers_present(self):
        from protocols.walk_shared.agents import WALK_AGENTS
        for key in EXPECTED_CORE_WALKERS:
            assert key in WALK_AGENTS, f"Missing core walker: {key}"

    def test_distant_specialists_present(self):
        from protocols.walk_shared.agents import WALK_AGENTS
        for key in EXPECTED_DISTANT_SPECIALISTS:
            assert key in WALK_AGENTS, f"Missing distant specialist: {key}"

    def test_required_fields(self):
        from protocols.walk_shared.agents import WALK_AGENTS
        for key, agent in WALK_AGENTS.items():
            assert "name" in agent, f"{key} missing 'name'"
            assert "system_prompt" in agent, f"{key} missing 'system_prompt'"
            assert isinstance(agent["name"], str)
            assert len(agent["system_prompt"]) > 20, f"{key} system_prompt too short"

    def test_walk_metadata_present(self):
        from protocols.walk_shared.agents import WALK_AGENTS
        for key, agent in WALK_AGENTS.items():
            meta = agent.get("walk_metadata")
            assert meta is not None, f"{key} missing walk_metadata"
            assert "lens_family" in meta, f"{key} walk_metadata missing lens_family"
            assert "core_transform" in meta, f"{key} walk_metadata missing core_transform"
            assert "default_depth_mode" in meta, f"{key} walk_metadata missing default_depth_mode"

    def test_lens_families_are_valid(self):
        from protocols.walk_shared.agents import WALK_AGENTS
        valid_families = {
            "meta", "systems", "analogical", "narrative", "constraint",
            "adversarial", "aesthetic", "historical", "complexity",
            "semiotic", "economic", "statistical",
        }
        for key, agent in WALK_AGENTS.items():
            family = agent["walk_metadata"]["lens_family"]
            assert family in valid_families, f"{key} has invalid lens_family: {family}"

    def test_depth_modes_are_valid(self):
        from protocols.walk_shared.agents import WALK_AGENTS
        valid_modes = {"shallow", "deep", "both", "frame", "score", "synthesize"}
        for key, agent in WALK_AGENTS.items():
            mode = agent["walk_metadata"]["default_depth_mode"]
            assert mode in valid_modes, f"{key} has invalid default_depth_mode: {mode}"

    def test_no_duplicate_names(self):
        from protocols.walk_shared.agents import WALK_AGENTS
        names = [a["name"] for a in WALK_AGENTS.values()]
        assert len(names) == len(set(names)), f"Duplicate agent names: {names}"


class TestWalkAgentRegistration:
    """Test that walk agents are properly registered in the master registry."""

    def test_walk_agents_in_builtin(self):
        from protocols.agents import BUILTIN_AGENTS
        for key in ALL_WALK_KEYS:
            assert key in BUILTIN_AGENTS, f"{key} not in BUILTIN_AGENTS"

    def test_walk_category_exists(self):
        from protocols.agents import AGENT_CATEGORIES
        assert "walk" in AGENT_CATEGORIES

    def test_walk_category_has_all_keys(self):
        from protocols.agents import AGENT_CATEGORIES
        walk_keys = set(AGENT_CATEGORIES["walk"])
        assert walk_keys == ALL_WALK_KEYS

    def test_build_agents_with_walk_category(self):
        """@walk category should expand to all 14 walk agents."""
        from protocols.agents import build_agents
        agents = build_agents(["@walk"], mode="research")
        assert len(agents) == 14
        names = {a["name"] for a in agents}
        assert "Systems Walker" in names
        assert "Salience Judge" in names
