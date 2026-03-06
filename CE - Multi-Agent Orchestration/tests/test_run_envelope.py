"""Tests for canonical run envelope extraction and cost telemetry."""

from __future__ import annotations

from dataclasses import dataclass

from protocols.cost_tracker import ProtocolCostTracker
from protocols.run_envelope import TelemetryWarning, build_run_envelope, extract_agent_outputs


@dataclass
class _Perspective:
    name: str
    response: str


@dataclass
class _SynthesisResult:
    perspectives: list[_Perspective]
    synthesis: str


@dataclass
class _RoundResponse:
    name: str
    response: str


@dataclass
class _Round:
    responses: list[_RoundResponse]


@dataclass
class _DebateResult:
    rounds: list[_Round]
    synthesis: str


def test_extract_agent_outputs_from_rounds() -> None:
    result = _DebateResult(
        rounds=[
            _Round(responses=[_RoundResponse(name="ceo", response="Round 1 CEO")]),
            _Round(responses=[_RoundResponse(name="cfo", response="Round 2 CFO")]),
        ],
        synthesis="Final synthesis",
    )
    outputs = extract_agent_outputs(result, agent_keys=["ceo", "cfo"])
    assert len(outputs) == 2
    assert outputs[0].round_number == 1
    assert outputs[1].round_number == 2
    assert outputs[0].agent_key == "ceo"
    assert outputs[1].agent_key == "cfo"


def test_build_run_envelope_attaches_cost_and_tool_events() -> None:
    result = _SynthesisResult(
        perspectives=[
            _Perspective(name="ceo", response="CEO analysis"),
            _Perspective(name="cfo", response="CFO analysis"),
        ],
        synthesis="Combined recommendation",
    )

    cost_summary = {
        "total_usd": 0.123,
        "calls": 2,
        "by_model": {
            "claude-haiku-4-5": {
                "calls": 2,
                "input_tokens": 1200,
                "output_tokens": 300,
                "cached_tokens": 0,
                "cost_usd": 0.123,
            }
        },
        "by_agent": {
            "ceo": {
                "calls": 1,
                "input_tokens": 600,
                "output_tokens": 150,
                "cached_tokens": 0,
                "cost_usd": 0.0615,
                "primary_model": "claude-haiku-4-5",
                "by_model": {},
            },
            "cfo": {
                "calls": 1,
                "input_tokens": 600,
                "output_tokens": 150,
                "cached_tokens": 0,
                "cost_usd": 0.0615,
                "primary_model": "claude-haiku-4-5",
                "by_model": {},
            },
        },
    }
    tool_events = [
        {
            "event": "tool_call",
            "agent_name": "ceo",
            "tool_name": "web_search",
            "tool_input": "{\"q\":\"market size\"}",
        },
        {
            "event": "tool_result",
            "agent_name": "ceo",
            "tool_name": "web_search",
            "result_preview": "search result",
        },
    ]

    env = build_run_envelope(
        protocol_key="p03_parallel_synthesis",
        question="Should we expand?",
        agent_keys=["ceo", "cfo"],
        result=result,
        source="api",
        cost_summary=cost_summary,
        tool_events=tool_events,
        warnings=[
            TelemetryWarning(
                code="langfuse_disabled",
                message="Langfuse disabled in test",
                component="langfuse",
            )
        ],
    )

    assert env.result_summary == "Combined recommendation"
    assert env.telemetry_degraded is True
    assert len(env.agent_outputs) == 2
    ceo_output = next(o for o in env.agent_outputs if o.agent_key == "ceo")
    assert ceo_output.cost_usd > 0
    assert ceo_output.input_tokens == 600
    assert len(ceo_output.tool_calls) == 2


def test_cost_tracker_summary_contains_by_agent() -> None:
    tracker = ProtocolCostTracker()
    tracker.track(
        model="claude-haiku-4-5",
        input_tokens=1000,
        output_tokens=250,
        cached_tokens=0,
        agent_name="CEO",
    )
    tracker.track(
        model="claude-haiku-4-5",
        input_tokens=500,
        output_tokens=100,
        cached_tokens=0,
        agent_name="CFO",
    )

    summary = tracker.summary()
    assert summary["calls"] == 2
    assert "by_agent" in summary
    assert "ceo" in summary["by_agent"]
    assert "cfo" in summary["by_agent"]
    assert summary["by_agent"]["ceo"]["calls"] == 1
