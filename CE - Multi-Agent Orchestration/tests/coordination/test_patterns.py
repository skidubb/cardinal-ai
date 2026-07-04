"""Tests for InteractionPattern schema and canonical topologies."""

from coordination.routing.patterns import (
    PATTERN_REGISTRY,
    InteractionPattern,
    PatternType,
)


class TestPatternRegistry:
    def test_all_nine_patterns_registered(self):
        assert len(PATTERN_REGISTRY) == 9

    def test_all_pattern_types_covered(self):
        for pt in PatternType:
            assert pt in PATTERN_REGISTRY

    def test_each_pattern_has_required_fields(self):
        for pt, pattern in PATTERN_REGISTRY.items():
            assert pattern.name, f"{pt} missing name"
            assert pattern.description, f"{pt} missing description"
            assert pattern.pattern_type == pt

    def test_debate_has_debater_and_judge_roles(self):
        debate = PATTERN_REGISTRY[PatternType.DEBATE]
        role_names = {r.role_name for r in debate.agent_roles}
        assert "debater" in role_names
        assert "judge" in role_names

    def test_open_conversation_has_high_turn_limit(self):
        oc = PATTERN_REGISTRY[PatternType.OPEN_CONVERSATION]
        assert oc.termination.max_rounds >= 20

    def test_pattern_serializes(self):
        for pattern in PATTERN_REGISTRY.values():
            data = pattern.model_dump()
            assert "pattern_type" in data
            assert "agent_roles" in data
            # Round-trip
            restored = InteractionPattern.model_validate(data)
            assert restored.pattern_type == pattern.pattern_type
