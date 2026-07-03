"""Tests for the P53 stigmergy protocol's pure helpers.

The LLM-driven waves need live API keys, but parse_traces / decay /
harvest_field / format_trace_field are all deterministic — proving them
end-to-end proves the "no central synthesizer" claim in the README.
"""

from __future__ import annotations

import json

import pytest

from protocols.p53_stigmergy.field import (
    DECAY_PER_WAVE,
    Trace,
    format_trace_field,
    harvest_field,
    parse_traces,
)


# ---------------------------------------------------------------------------
# parse_traces
# ---------------------------------------------------------------------------

def test_parse_traces_happy_path() -> None:
    text = json.dumps([
        {"type": "risk", "location": "regulatory-risk", "strength": 0.9,
         "content": "GDPR penalties are up to 4% of global revenue."},
        {"type": "opportunity", "location": "cross-sell", "strength": 0.6,
         "content": "Existing customers ask for adjacent product."},
    ])
    traces = parse_traces(text, author="CFO", wave=1)
    assert len(traces) == 2
    assert {t.trace_type for t in traces} == {"risk", "opportunity"}
    assert all(t.author == "CFO" and t.wave == 1 for t in traces)


def test_parse_traces_handles_markdown_fence() -> None:
    text = (
        "Here is my analysis:\n"
        "```json\n"
        '[{"type": "insight", "location": "team-capacity", "strength": 0.6,'
        ' "content": "Sales team lacks EU compliance training."}]\n'
        "```\n"
    )
    traces = parse_traces(text, author="COO", wave=2)
    assert len(traces) == 1
    assert traces[0].trace_type == "insight"


def test_parse_traces_skips_invalid_items() -> None:
    text = json.dumps([
        {"type": "risk", "location": "x", "strength": 0.6, "content": "valid"},
        {"type": "not-a-real-type", "location": "y", "strength": 0.6, "content": "invalid type"},
        {"type": "risk", "location": "", "strength": 0.6, "content": "missing location"},
        {"type": "risk", "location": "z", "strength": 0.0, "content": "zero strength"},
        {"type": "risk", "location": "w", "strength": 0.6, "content": ""},
        "not a dict",
    ])
    traces = parse_traces(text, author="CTO", wave=1)
    assert len(traces) == 1
    assert traces[0].content == "valid"


def test_parse_traces_clamps_strength() -> None:
    text = json.dumps([
        {"type": "risk", "location": "x", "strength": 5.0, "content": "over"},
        {"type": "risk", "location": "y", "strength": -1.0, "content": "under"},
    ])
    traces = parse_traces(text, author="A", wave=1)
    # under=0 gets filtered as zero-strength; over should clamp to 1.0.
    assert len(traces) == 1
    assert traces[0].strength == 1.0


def test_parse_traces_no_json_returns_empty() -> None:
    assert parse_traces("just prose, no JSON here", author="A", wave=1) == []


# ---------------------------------------------------------------------------
# Trace.decayed_strength
# ---------------------------------------------------------------------------

def test_decay_applies_per_wave_gap() -> None:
    t = Trace(trace_type="risk", location="x", strength=1.0,
              content="c", author="A", wave=1)
    assert t.decayed_strength(1) == 1.0
    assert t.decayed_strength(2) == pytest.approx(DECAY_PER_WAVE)
    assert t.decayed_strength(3) == pytest.approx(DECAY_PER_WAVE ** 2)
    # No negative decay when reading at an earlier wave.
    assert t.decayed_strength(0) == 1.0


# ---------------------------------------------------------------------------
# harvest_field — the "no central synthesizer" invariant
# ---------------------------------------------------------------------------

def _t(trace_type: str, location: str, strength: float, author: str, wave: int) -> Trace:
    return Trace(trace_type=trace_type, location=location, strength=strength,
                 content=f"{author}:{location}@{wave}", author=author, wave=wave)


def test_harvest_groups_by_type_and_location() -> None:
    traces = [
        _t("risk", "reg", 0.9, "CFO", 1),
        _t("risk", "reg", 0.6, "CEO", 2),
        _t("risk", "reg", 0.3, "CRO", 3),
        _t("opportunity", "cross-sell", 0.6, "CMO", 1),
    ]
    field = harvest_field(traces, top_n_per_type=3)
    assert len(field["risk"]) == 1
    assert field["risk"][0].location == "reg"
    assert field["risk"][0].trace_count == 3
    assert set(field["risk"][0].contributors) == {"CFO", "CEO", "CRO"}
    assert len(field["opportunity"]) == 1


def test_harvest_ranks_locations_by_cumulative_strength() -> None:
    traces = [
        _t("risk", "cold", 0.3, "A", 3),
        _t("risk", "hot", 0.6, "B", 3),
        _t("risk", "hot", 0.6, "C", 3),
        _t("risk", "hot", 0.6, "D", 3),
    ]
    field = harvest_field(traces, top_n_per_type=5)
    assert [s.location for s in field["risk"]] == ["hot", "cold"]
    assert field["risk"][0].cumulative_strength > field["risk"][1].cumulative_strength


def test_harvest_respects_top_n() -> None:
    traces = [_t("risk", f"loc-{i}", 0.6, "A", 1) for i in range(10)]
    field = harvest_field(traces, top_n_per_type=3)
    assert len(field["risk"]) == 3


def test_harvest_empty_returns_all_types() -> None:
    field = harvest_field([])
    assert set(field.keys()) >= {"risk", "opportunity", "constraint", "insight", "question"}
    assert all(v == [] for v in field.values())


def test_harvest_uses_max_wave_for_decay() -> None:
    """A wave-1 trace should count less than a wave-3 trace at harvest."""
    traces = [
        _t("risk", "early", 0.9, "A", 1),  # decays over 2 waves
        _t("risk", "late", 0.4, "B", 3),   # no decay
    ]
    field = harvest_field(traces, top_n_per_type=2)
    # Early trace decayed: 0.9 * 0.6^2 = 0.324. Late trace: 0.4. Late wins.
    assert [s.location for s in field["risk"]] == ["late", "early"]


# ---------------------------------------------------------------------------
# format_trace_field
# ---------------------------------------------------------------------------

def test_format_trace_field_empty() -> None:
    assert "empty" in format_trace_field([], current_wave=1)


def test_format_trace_field_ranks_by_cumulative_strength() -> None:
    traces = [
        _t("risk", "weak", 0.3, "A", 1),
        _t("risk", "strong", 0.9, "B", 1),
    ]
    formatted = format_trace_field(traces, current_wave=1)
    assert formatted.index("strong") < formatted.index("weak")


# ---------------------------------------------------------------------------
# End-to-end field convergence (mechanical, no LLM)
# ---------------------------------------------------------------------------

def test_field_amplifies_convergent_locations() -> None:
    """Three agents dropping traces on the same location must outrank one
    agent dropping a single stronger trace elsewhere.
    """
    traces = [
        _t("risk", "convergent", 0.6, "A", 1),
        _t("risk", "convergent", 0.6, "B", 1),
        _t("risk", "convergent", 0.6, "C", 1),
        _t("risk", "lone-wolf", 0.9, "D", 1),
    ]
    field = harvest_field(traces, top_n_per_type=2)
    assert field["risk"][0].location == "convergent"
    assert field["risk"][0].cumulative_strength > field["risk"][1].cumulative_strength
