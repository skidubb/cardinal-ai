"""Tests for the auto-score writer.

Proves the second half of the learning loop:
  persist_run → auto_score → weights.json → router_weights → P0a router
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from protocols import auto_score, router_weights


@pytest.fixture(autouse=True)
def isolated_weights(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    weights_file = tmp_path / "weights.json"
    monkeypatch.setattr(router_weights, "WEIGHTS_PATH", str(weights_file))
    monkeypatch.setattr(auto_score, "WEIGHTS_PATH", str(weights_file))
    return weights_file


_SENTINEL: list[str] = []


def _envelope(
    *,
    protocol_key: str = "p16_ach",
    agent_keys: list[str] | None | list = None,
    status: str = "completed",
    result_summary: str = "A synthesis with enough content to look substantive." * 8,
    total_cost: float = 0.05,
    agent_output_count: int = 3,
) -> SimpleNamespace:
    outputs = [
        SimpleNamespace(text=f"Agent {i} said something useful and specific." * 4)
        for i in range(agent_output_count)
    ]
    # Distinguish "not supplied" (use default) from "explicitly empty".
    resolved_agents = ["ceo", "cfo", "cto"] if agent_keys is None else list(agent_keys)
    return SimpleNamespace(
        protocol_key=protocol_key,
        agent_keys=resolved_agents,
        question="Should we expand into Europe?",
        status=status,
        result_summary=result_summary,
        result_json={},
        cost={"total_usd": total_cost},
        agent_outputs=outputs,
        metadata={},
    )


@pytest.mark.asyncio
async def test_heuristic_scores_completed_run_high(isolated_weights: Path) -> None:
    env = _envelope(status="completed", total_cost=0.05)
    result = await auto_score.auto_score_and_record(env)
    assert result.scored
    assert result.backend == "heuristic"
    assert result.score is not None and result.score >= 0.7


@pytest.mark.asyncio
async def test_heuristic_scores_failed_run_low(isolated_weights: Path) -> None:
    env = _envelope(
        status="failed",
        result_summary="",
        agent_output_count=0,
        total_cost=1.5,
    )
    result = await auto_score.auto_score_and_record(env)
    # status=failed → status_term=0, missing synthesis → 0, no agents → 0,
    # high cost → small cost_term. Score should be near-zero.
    assert result.scored
    assert result.score is not None and result.score < 0.2


@pytest.mark.asyncio
async def test_backend_off_disables_loop(
    isolated_weights: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(auto_score.BACKEND_ENV_VAR, "off")
    result = await auto_score.auto_score_and_record(_envelope())
    assert not result.scored
    assert result.backend == "off"
    assert not isolated_weights.exists()


@pytest.mark.asyncio
async def test_writes_one_record_per_agent(isolated_weights: Path) -> None:
    env = _envelope(agent_keys=["ceo", "cfo", "cto", "cmo"])
    await auto_score.auto_score_and_record(env, problem_type="Diagnostic")
    data = json.loads(isolated_weights.read_text())
    assert len(data["records"]) == 4
    assert {r["agent"] for r in data["records"]} == {"ceo", "cfo", "cto", "cmo"}
    for r in data["records"]:
        assert r["protocol"] == "p16_ach"
        assert r["problem_type"] == "Diagnostic"
        assert r["source"] == "auto_score"
        assert 0.0 <= r["score"] <= 1.0


@pytest.mark.asyncio
async def test_end_to_end_loop_closes(isolated_weights: Path) -> None:
    """The full loop: auto-score writes → router_weights reads → override fires."""

    # Score 6 runs of P16 (Diagnostic) at high quality.
    for _ in range(6):
        await auto_score.auto_score_and_record(
            _envelope(protocol_key="p16_ach", total_cost=0.05),
            problem_type="Diagnostic",
        )
    # Score 6 runs of P4 at low quality (failed).
    for _ in range(6):
        await auto_score.auto_score_and_record(
            _envelope(
                protocol_key="p04_multi_round_debate",
                status="failed",
                result_summary="",
                agent_output_count=0,
                total_cost=1.5,
            ),
            problem_type="Diagnostic",
        )

    perf = router_weights.performance_by_protocol("Diagnostic")
    assert "p16_ach" in perf and "p04_multi_round_debate" in perf
    assert perf["p16_ach"].mean_score > perf["p04_multi_round_debate"].mean_score

    override, rationale = router_weights.suggest_override(
        "p04_multi_round_debate", perf
    )
    assert override == "p16_ach"
    assert rationale is not None


@pytest.mark.asyncio
async def test_infer_problem_type_from_protocol(isolated_weights: Path) -> None:
    env = _envelope(protocol_key="p32_tetlock_forecast")
    result = await auto_score.auto_score_and_record(env)
    assert result.problem_type == "Estimation"


@pytest.mark.asyncio
async def test_infer_problem_type_falls_back_to_general(isolated_weights: Path) -> None:
    env = _envelope(protocol_key="p_unknown_protocol")
    result = await auto_score.auto_score_and_record(env)
    assert result.problem_type == "general"


@pytest.mark.asyncio
async def test_missing_agent_keys_skips_write(isolated_weights: Path) -> None:
    env = _envelope(agent_keys=[])
    result = await auto_score.auto_score_and_record(env)
    assert not result.scored
    assert result.reason == "missing_protocol_or_agents"
    assert not isolated_weights.exists()
