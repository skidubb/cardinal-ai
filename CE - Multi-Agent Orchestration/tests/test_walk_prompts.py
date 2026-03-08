"""Tests for walk_shared.prompts — shared prompt templates."""

from __future__ import annotations

import pytest


class TestSharedPrompts:
    def test_all_prompts_defined(self):
        from protocols.walk_shared.prompts import (
            FRAME_PROMPT, SHALLOW_WALK_PROMPT, SALIENCE_JUDGE_PROMPT,
            DEEP_WALK_PROMPT, CROSS_EXAM_PROMPT, SYNTHESIS_PROMPT,
        )
        for name, prompt in [
            ("FRAME_PROMPT", FRAME_PROMPT),
            ("SHALLOW_WALK_PROMPT", SHALLOW_WALK_PROMPT),
            ("SALIENCE_JUDGE_PROMPT", SALIENCE_JUDGE_PROMPT),
            ("DEEP_WALK_PROMPT", DEEP_WALK_PROMPT),
            ("CROSS_EXAM_PROMPT", CROSS_EXAM_PROMPT),
            ("SYNTHESIS_PROMPT", SYNTHESIS_PROMPT),
        ]:
            assert isinstance(prompt, str), f"{name} is not a string"
            assert len(prompt) > 50, f"{name} is suspiciously short"

    def test_frame_prompt_has_placeholders(self):
        from protocols.walk_shared.prompts import FRAME_PROMPT
        assert "{question}" in FRAME_PROMPT

    def test_shallow_walk_prompt_has_placeholders(self):
        from protocols.walk_shared.prompts import SHALLOW_WALK_PROMPT
        assert "{question}" in SHALLOW_WALK_PROMPT
        assert "{frame_json}" in SHALLOW_WALK_PROMPT
        assert "{lens_family}" in SHALLOW_WALK_PROMPT

    def test_salience_judge_prompt_has_placeholders(self):
        from protocols.walk_shared.prompts import SALIENCE_JUDGE_PROMPT
        assert "{shallow_outputs_json}" in SALIENCE_JUDGE_PROMPT
        assert "{frame_json}" in SALIENCE_JUDGE_PROMPT

    def test_deep_walk_prompt_has_placeholders(self):
        from protocols.walk_shared.prompts import DEEP_WALK_PROMPT
        assert "{question}" in DEEP_WALK_PROMPT
        assert "{frame_json}" in DEEP_WALK_PROMPT

    def test_cross_exam_prompt_has_placeholders(self):
        from protocols.walk_shared.prompts import CROSS_EXAM_PROMPT
        assert "{target_deep_output_json}" in CROSS_EXAM_PROMPT

    def test_synthesis_prompt_has_placeholders(self):
        from protocols.walk_shared.prompts import SYNTHESIS_PROMPT
        assert "{question}" in SYNTHESIS_PROMPT

    def test_frame_prompt_formats_cleanly(self):
        from protocols.walk_shared.prompts import FRAME_PROMPT
        result = FRAME_PROMPT.format(question="Should we expand?")
        assert "Should we expand?" in result

    def test_shallow_walk_prompt_enforces_reframe_not_solve(self):
        from protocols.walk_shared.prompts import SHALLOW_WALK_PROMPT
        lower = SHALLOW_WALK_PROMPT.lower()
        assert "reframe" in lower or "do not solve" in lower
