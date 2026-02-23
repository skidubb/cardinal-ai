"""Tests for rubric loading and prompt building."""

import tempfile
from pathlib import Path

import yaml

from ce_evals.core.rubric import Rubric


def _make_rubric_yaml() -> str:
    return yaml.dump({
        "name": "Test Rubric",
        "dimensions": [
            {"name": "clarity", "description": "How clear is the response"},
            {"name": "depth", "description": "How deep is the analysis"},
        ],
        "judge_system_prompt": "Evaluate on:\n{{dimensions}}",
    })


def test_from_yaml_loads_dimensions():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(_make_rubric_yaml())
        f.flush()
        rubric = Rubric.from_yaml(f.name)

    assert rubric.name == "Test Rubric"
    assert len(rubric.dimensions) == 2
    assert rubric.dimension_names == ["clarity", "depth"]


def test_build_judge_prompt_injects_dimensions():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(_make_rubric_yaml())
        f.flush()
        rubric = Rubric.from_yaml(f.name)

    prompt = rubric.build_judge_prompt()
    assert "Clarity" in prompt
    assert "Depth" in prompt
    assert "{{dimensions}}" not in prompt


def test_fallback_prompt_without_template():
    rubric = Rubric(
        name="Bare",
        dimensions=[{"name": "quality", "description": "Overall quality"}],
        judge_system_prompt="",
    )
    prompt = rubric.build_judge_prompt()
    assert "Quality" in prompt
    assert "JSON" in prompt
