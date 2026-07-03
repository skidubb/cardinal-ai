"""Unit tests for the router→weights loop.

Proves that historical performance recorded by P45 flows into the P0a routing
decision. No live LLM calls — the reader/override logic is pure Python.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from protocols import router_weights


@pytest.fixture
def isolated_weights(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    weights_file = tmp_path / "weights.json"
    monkeypatch.setattr(router_weights, "WEIGHTS_PATH", str(weights_file))
    return weights_file


def _write(weights_file: Path, records: list[dict]) -> None:
    weights_file.write_text(json.dumps({"records": records}))


def test_no_file_returns_empty(isolated_weights: Path) -> None:
    assert router_weights.performance_by_protocol("Diagnostic") == {}
    assert router_weights.format_for_prompt({}) == ""
    override, rationale = router_weights.suggest_override("P16", {})
    assert override is None and rationale is None


def test_aggregates_by_protocol_and_problem_type(isolated_weights: Path) -> None:
    _write(
        isolated_weights,
        [
            {"agent": "ceo", "protocol": "P16", "problem_type": "Diagnostic", "score": 0.9},
            {"agent": "cfo", "protocol": "P16", "problem_type": "Diagnostic", "score": 0.8},
            {"agent": "cto", "protocol": "P4", "problem_type": "Diagnostic", "score": 0.4},
            {"agent": "ceo", "protocol": "P16", "problem_type": "Exploration", "score": 0.2},
        ],
    )
    perf = router_weights.performance_by_protocol("Diagnostic")
    assert set(perf.keys()) == {"P16", "P4"}
    assert perf["P16"].sample_count == 2
    assert perf["P16"].mean_score == pytest.approx(0.85)
    assert perf["P4"].sample_count == 1


def test_override_fires_when_alternative_dominates(isolated_weights: Path) -> None:
    _write(
        isolated_weights,
        [{"agent": f"a{i}", "protocol": "P16", "problem_type": "Diagnostic", "score": 0.9}
         for i in range(router_weights.MIN_SAMPLES_FOR_OVERRIDE)]
        + [{"agent": f"a{i}", "protocol": "P4", "problem_type": "Diagnostic", "score": 0.5}
           for i in range(router_weights.MIN_SAMPLES_FOR_OVERRIDE)],
    )
    perf = router_weights.performance_by_protocol("Diagnostic")
    override, rationale = router_weights.suggest_override("P4", perf)
    assert override == "P16"
    assert rationale and "P16" in rationale and "P4" in rationale


def test_override_skipped_when_gap_is_small(isolated_weights: Path) -> None:
    _write(
        isolated_weights,
        [{"agent": f"a{i}", "protocol": "P16", "problem_type": "Diagnostic", "score": 0.72}
         for i in range(router_weights.MIN_SAMPLES_FOR_OVERRIDE)]
        + [{"agent": f"a{i}", "protocol": "P4", "problem_type": "Diagnostic", "score": 0.70}
           for i in range(router_weights.MIN_SAMPLES_FOR_OVERRIDE)],
    )
    perf = router_weights.performance_by_protocol("Diagnostic")
    override, _ = router_weights.suggest_override("P4", perf)
    assert override is None


def test_override_skipped_when_sample_too_small(isolated_weights: Path) -> None:
    _write(
        isolated_weights,
        [{"agent": "a", "protocol": "P16", "problem_type": "Diagnostic", "score": 0.95}]
        + [{"agent": f"a{i}", "protocol": "P4", "problem_type": "Diagnostic", "score": 0.5}
           for i in range(router_weights.MIN_SAMPLES_FOR_OVERRIDE)],
    )
    perf = router_weights.performance_by_protocol("Diagnostic")
    override, _ = router_weights.suggest_override("P4", perf)
    assert override is None


def test_override_skipped_when_llm_choice_unranked(isolated_weights: Path) -> None:
    _write(
        isolated_weights,
        [{"agent": f"a{i}", "protocol": "P16", "problem_type": "Diagnostic", "score": 0.95}
         for i in range(router_weights.MIN_SAMPLES_FOR_OVERRIDE)],
    )
    perf = router_weights.performance_by_protocol("Diagnostic")
    override, _ = router_weights.suggest_override("P4", perf)
    assert override is None


def test_format_for_prompt_ranks_best_first(isolated_weights: Path) -> None:
    _write(
        isolated_weights,
        [
            {"agent": "a", "protocol": "P4", "problem_type": "Diagnostic", "score": 0.4},
            {"agent": "b", "protocol": "P16", "problem_type": "Diagnostic", "score": 0.9},
        ],
    )
    perf = router_weights.performance_by_protocol("Diagnostic")
    prompt = router_weights.format_for_prompt(perf)
    assert prompt.index("P16") < prompt.index("P4")


def test_malformed_file_returns_empty(isolated_weights: Path) -> None:
    isolated_weights.write_text("not valid json")
    assert router_weights.performance_by_protocol("Diagnostic") == {}
