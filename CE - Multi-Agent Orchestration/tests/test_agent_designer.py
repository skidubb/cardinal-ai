"""Tests for protocols/agent_designer.py — validation layer and public API."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from protocols.agent_designer import (
    _EMPTY_SUGGESTION,
    _slugify_key,
    _validate_suggestion,
    suggest_agents,
    suggest_agents_batch,
)
from protocols.config import THINKING_MODEL

FAKE_BENCH = {
    "cfo": {"name": "CFO", "category": "executive"},
    "cto": {"name": "CTO", "category": "executive"},
    "ceo": {"name": "CEO", "category": "executive"},
}

VALID_TOOLS = {"web_search", "web_fetch", "sec_edgar"}

LONG_PROMPT = "x" * 250


# ── _slugify_key ─────────────────────────────────────────────────────────────


def test_slugify_key_basic():
    assert _slugify_key("Spectrum Policy!", set()) == "spectrum_policy"


def test_slugify_key_collision_gets_suffix():
    assert _slugify_key("spectrum_policy", {"spectrum_policy"}) == "spectrum_policy_2"


def test_slugify_key_collision_skips_taken_suffixes():
    taken = {"spectrum_policy", "spectrum_policy_2"}
    assert _slugify_key("spectrum_policy", taken) == "spectrum_policy_3"


def test_slugify_key_empty_becomes_agent():
    assert _slugify_key("", set()) == "agent"
    assert _slugify_key("   ", set()) == "agent"
    assert _slugify_key("!!!", set()) == "agent"


# ── _validate_suggestion — existing_agents ───────────────────────────────────


def test_validate_existing_agents_drops_unknown_keys():
    raw = {
        "existing_agents": [
            {"key": "cfo", "score": 0.8, "rationale": "good fit"},
            {"key": "not_a_real_agent", "score": 0.9, "rationale": "n/a"},
        ]
    }
    result = _validate_suggestion(raw, set(FAKE_BENCH), VALID_TOOLS)
    keys = [e["key"] for e in result["existing_agents"]]
    assert keys == ["cfo"]


def test_validate_existing_agents_clamps_scores():
    raw = {
        "existing_agents": [
            {"key": "cfo", "score": 5.0, "rationale": "over"},
            {"key": "cto", "score": -3.0, "rationale": "under"},
        ]
    }
    result = _validate_suggestion(raw, set(FAKE_BENCH), VALID_TOOLS)
    by_key = {e["key"]: e["score"] for e in result["existing_agents"]}
    assert by_key["cfo"] == 1.0
    assert by_key["cto"] == 0.0


def test_validate_existing_agents_bad_score_defaults_zero():
    raw = {
        "existing_agents": [{"key": "cfo", "score": "not-a-number", "rationale": "x"}]
    }
    result = _validate_suggestion(raw, set(FAKE_BENCH), VALID_TOOLS)
    assert result["existing_agents"][0]["score"] == 0.0


def test_validate_existing_agents_sorted_desc():
    raw = {
        "existing_agents": [
            {"key": "cfo", "score": 0.2, "rationale": "low"},
            {"key": "cto", "score": 0.9, "rationale": "high"},
            {"key": "ceo", "score": 0.5, "rationale": "mid"},
        ]
    }
    result = _validate_suggestion(raw, set(FAKE_BENCH), VALID_TOOLS)
    scores = [e["score"] for e in result["existing_agents"]]
    assert scores == sorted(scores, reverse=True)
    assert [e["key"] for e in result["existing_agents"]] == ["cto", "ceo", "cfo"]


# ── _validate_suggestion — new_agents ─────────────────────────────────────────


def _new_agent_spec(**overrides):
    spec = {
        "key": "spectrum_policy_analyst",
        "name": "Spectrum Policy Analyst",
        "category": "custom",
        "model": "claude-opus-4-8",
        "temperature": 1.0,
        "system_prompt": LONG_PROMPT,
        "tools": ["web_search"],
        "kb_namespaces": [],
        "rationale": "fills a gap",
    }
    spec.update(overrides)
    return spec


def test_validate_new_agent_thin_prompt_dropped():
    raw = {"new_agents": [_new_agent_spec(system_prompt="too short")]}
    result = _validate_suggestion(raw, set(FAKE_BENCH), VALID_TOOLS)
    assert result["new_agents"] == []


def test_validate_new_agent_unknown_model_coerced_to_thinking_model():
    raw = {"new_agents": [_new_agent_spec(model="not-a-real-model")]}
    result = _validate_suggestion(raw, set(FAKE_BENCH), VALID_TOOLS)
    assert result["new_agents"][0]["model"] == THINKING_MODEL


def test_validate_new_agent_invalid_tools_dropped_valid_kept():
    raw = {
        "new_agents": [
            _new_agent_spec(tools=["web_search", "not_a_real_tool", "web_fetch"])
        ]
    }
    result = _validate_suggestion(raw, set(FAKE_BENCH), VALID_TOOLS)
    assert result["new_agents"][0]["tools"] == ["web_search", "web_fetch"]


def test_validate_new_agent_gateway_model_forces_no_tools():
    raw = {
        "new_agents": [
            _new_agent_spec(
                model="deepseek-v4-flash", tools=["web_search", "web_fetch"]
            )
        ]
    }
    result = _validate_suggestion(raw, set(FAKE_BENCH), VALID_TOOLS)
    assert result["new_agents"][0]["model"] == "deepseek-v4-flash"
    assert result["new_agents"][0]["tools"] == []


def test_validate_new_agent_key_collision_with_bench_key_suffixed():
    raw = {"new_agents": [_new_agent_spec(key="cfo")]}
    result = _validate_suggestion(raw, set(FAKE_BENCH), VALID_TOOLS)
    assert result["new_agents"][0]["key"] == "cfo_2"


# ── _validate_suggestion — team ───────────────────────────────────────────────


def test_validate_team_filters_to_bench_and_new_keys():
    raw = {
        "new_agents": [_new_agent_spec(key="spectrum_policy_analyst")],
        "team": {
            "name": "Spectrum Team",
            "description": "desc",
            "agent_keys": ["cfo", "spectrum_policy_analyst", "not_a_real_agent"],
        },
    }
    result = _validate_suggestion(raw, set(FAKE_BENCH), VALID_TOOLS)
    assert result["team"]["agent_keys"] == ["cfo", "spectrum_policy_analyst"]


def test_validate_team_none_when_all_keys_invalid():
    raw = {
        "team": {
            "name": "Bad Team",
            "description": "desc",
            "agent_keys": ["not_a_real_agent", "also_fake"],
        }
    }
    result = _validate_suggestion(raw, set(FAKE_BENCH), VALID_TOOLS)
    assert result["team"] is None


def test_validate_team_missing_or_non_dict_is_none():
    assert _validate_suggestion({}, set(FAKE_BENCH), VALID_TOOLS)["team"] is None
    assert (
        _validate_suggestion({"team": "not-a-dict"}, set(FAKE_BENCH), VALID_TOOLS)[
            "team"
        ]
        is None
    )


# ── suggest_agents / suggest_agents_batch ─────────────────────────────────────


@pytest.fixture(autouse=True)
def _patch_bench(monkeypatch):
    """Keep designer tests hermetic — _bench_entries otherwise touches the DB."""
    monkeypatch.setattr(
        "protocols.agent_designer._bench_entries", lambda: dict(FAKE_BENCH)
    )
    monkeypatch.setattr(
        "protocols.agent_designer._tool_catalog_block",
        lambda: ("(fake tool catalog)", set(VALID_TOOLS)),
    )


@pytest.mark.asyncio
async def test_suggest_agents_end_to_end():
    fake_response = (
        '{"existing_agents": [{"key": "cfo", "score": 0.8, "rationale": "fits"}], '
        '"new_agents": [], "team": {"name": "Team", "description": "d", '
        '"agent_keys": ["cfo"]}}'
    )
    with patch(
        "protocols.agent_designer.llm_complete",
        new=AsyncMock(return_value=fake_response),
    ):
        result = await suggest_agents("Should we expand?", client=object())
    assert result["existing_agents"][0]["key"] == "cfo"
    assert result["team"]["agent_keys"] == ["cfo"]


@pytest.mark.asyncio
async def test_suggest_agents_returns_empty_on_llm_failure():
    with patch(
        "protocols.agent_designer.llm_complete",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    ):
        result = await suggest_agents("Should we expand?", client=object())
    assert result == _EMPTY_SUGGESTION


@pytest.mark.asyncio
async def test_suggest_agents_batch_returns_empty_list_for_no_questions():
    assert await suggest_agents_batch([]) == []


@pytest.mark.asyncio
async def test_suggest_agents_batch_aligned_and_missing_index_is_empty():
    fake_response = (
        '{"suggestions": ['
        '{"question_index": 1, "existing_agents": [{"key": "ceo", "score": 0.7, '
        '"rationale": "fits"}], "new_agents": [], "team": null}'
        "]}"
    )
    with patch(
        "protocols.agent_designer.llm_complete",
        new=AsyncMock(return_value=fake_response),
    ):
        results = await suggest_agents_batch(
            ["Question A?", "Question B?", "Question C?"], client=object()
        )
    assert len(results) == 3
    assert results[0] == _EMPTY_SUGGESTION
    assert results[1]["existing_agents"][0]["key"] == "ceo"
    assert results[2] == _EMPTY_SUGGESTION


@pytest.mark.asyncio
async def test_suggest_agents_batch_new_agent_reattached_when_redefined_in_team_item():
    """A new agent fully defined in Q0 and *redefined* (same key, full spec) in
    Q1's own new_agents dedupes to the earlier definition via defined_new.

    NOTE: this is the only path that actually exercises the reattachment
    branch in ``suggest_agents_batch``. If Q1 only *references* the key in
    its team (without redefining new_agents), ``_validate_suggestion`` strips
    the unknown key from ``team.agent_keys`` before the outer reattachment
    loop ever runs — see ``test_suggest_agents_batch_team_only_reference_to_earlier_new_agent_is_dropped``
    for that (likely unintended) behavior.
    """
    new_agent = _new_agent_spec(key="spectrum_policy_analyst")
    fake_response = (
        '{"suggestions": ['
        '{"question_index": 0, "existing_agents": [], '
        f'"new_agents": [{_json(new_agent)}], "team": null}},'
        '{"question_index": 1, "existing_agents": [], '
        f'"new_agents": [{_json(new_agent)}], '
        '"team": {"name": "T", "description": "d", '
        '"agent_keys": ["cfo", "spectrum_policy_analyst"]}}'
        "]}"
    )
    with patch(
        "protocols.agent_designer.llm_complete",
        new=AsyncMock(return_value=fake_response),
    ):
        results = await suggest_agents_batch(
            ["Question A?", "Question B?"], client=object()
        )
    q0, q1 = results
    assert q0["new_agents"][0]["key"] == "spectrum_policy_analyst"
    assert q1["new_agents"][0]["key"] == "spectrum_policy_analyst"
    assert "spectrum_policy_analyst" in q1["team"]["agent_keys"]


@pytest.mark.asyncio
async def test_suggest_agents_batch_team_only_reference_to_earlier_new_agent_is_dropped():
    """Documents current (likely buggy) behavior: when Q1's team references a
    new-agent key defined only in Q0 — without redefining it in Q1's own
    new_agents — ``_validate_suggestion`` drops the unknown key from
    ``team.agent_keys`` before ``suggest_agents_batch``'s cross-item
    ``defined_new`` reattachment ever sees it. The reattachment branch is
    unreachable for pure cross-item references; it only fires when the key
    is redefined in the same item (see the test above), at which point it's
    already present and reattachment is a no-op.
    """
    new_agent = _new_agent_spec(key="spectrum_policy_analyst")
    fake_response = (
        '{"suggestions": ['
        '{"question_index": 0, "existing_agents": [], '
        f'"new_agents": [{_json(new_agent)}], "team": null}},'
        '{"question_index": 1, "existing_agents": [], "new_agents": [], '
        '"team": {"name": "T", "description": "d", '
        '"agent_keys": ["cfo", "spectrum_policy_analyst"]}}'
        "]}"
    )
    with patch(
        "protocols.agent_designer.llm_complete",
        new=AsyncMock(return_value=fake_response),
    ):
        results = await suggest_agents_batch(
            ["Question A?", "Question B?"], client=object()
        )
    q0, q1 = results
    assert q0["new_agents"][0]["key"] == "spectrum_policy_analyst"
    assert q1["new_agents"] == []
    assert q1["team"]["agent_keys"] == ["cfo"]


def _json(d: dict) -> str:
    import json

    return json.dumps(d)
