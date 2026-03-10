"""Unit tests for ProtocolReport dataclass and from_envelope transform.

These tests follow the TDD RED phase — they define the expected behavior
of protocols/protocol_report.py before the implementation exists.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from protocols.protocol_report import (
    AgentContribution,
    ProtocolReport,
    confidence_label,
    extract_disagreements,
    extract_key_findings,
    from_envelope,
)
from protocols.run_envelope import AgentOutputEnvelope, RunEnvelope


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _utc(year: int = 2025, month: int = 1, day: int = 1) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


SAMPLE_SUMMARY = """\
This is the executive summary paragraph.

Key findings from the analysis:
- The market opportunity is significant
- Revenue growth is projected at 15% YoY
- However, the CFO noted concerns about cash flow

The CEO agreed overall, but in contrast, the CTO dissented on timeline.
The COO provided an alternative view on operations.
"""

SAMPLE_SUMMARY_NO_SIGNALS = """\
All agents agreed on the approach.

- Focus on growth
- Optimize operations

No major disagreements were found in this analysis.
"""


@pytest.fixture
def sample_agent_outputs() -> list[AgentOutputEnvelope]:
    return [
        AgentOutputEnvelope(
            agent_key="ceo",
            agent_name="CEO",
            text="The strategic opportunity is clear.",
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.01,
            tool_calls=[{"tool_name": "web_search", "result_preview": "found"}],
        ),
        AgentOutputEnvelope(
            agent_key="cfo",
            agent_name="CFO",
            text="Revenue projections support the expansion.",
            model="claude-opus-4-6",
            input_tokens=80,
            output_tokens=40,
            cost_usd=0.008,
        ),
        AgentOutputEnvelope(
            agent_key="_synthesis",
            agent_name="Synthesis",
            text="Internal synthesis node.",
            model="claude-haiku-4-5-20251001",
            input_tokens=10,
            output_tokens=5,
            cost_usd=0.0001,
        ),
        AgentOutputEnvelope(
            agent_key="_result",
            agent_name="Result",
            text="Internal result node.",
        ),
        AgentOutputEnvelope(
            agent_key="_stage",
            agent_name="Stage",
            text="Internal stage node.",
        ),
    ]


@pytest.fixture
def sample_envelope(sample_agent_outputs) -> RunEnvelope:
    return RunEnvelope(
        protocol_key="p03_parallel_synthesis",
        question="Should we expand into Europe?",
        agent_keys=["ceo", "cfo", "cto"],
        source="api",
        status="completed",
        started_at=_utc(2025, 1, 1),
        completed_at=_utc(2025, 1, 1),
        result_json={"synthesis": SAMPLE_SUMMARY},
        result_summary=SAMPLE_SUMMARY,
        cost={"total_usd": 0.018, "calls": 5, "by_model": {"claude-opus-4-6": 0.018}},
        trace_id="trace-abc-123",
        run_id=42,
        agent_outputs=sample_agent_outputs,
    )


@pytest.fixture
def sample_verdict() -> dict:
    return {
        "overall": 4,
        "completeness": 4,
        "consistency": 3,
        "actionability": 5,
        "recommendation": "accept",
        "flags": [],
        "rationale": "Good synthesis.",
    }


# ── Test: ProtocolReport fields ────────────────────────────────────────────────

def test_protocol_report_fields():
    """ProtocolReport has all required fields with correct types."""
    report = ProtocolReport(
        participants=["ceo", "cfo"],
        executive_summary="Summary here.",
        key_findings=["Finding 1", "Finding 2"],
        disagreements=["Disagreement 1"],
        confidence_score=4,
        confidence_label_str="High",
        synthesis="Full synthesis text.",
        agent_contributions=[],
        cost_summary={"total_usd": 0.01},
        metadata={"protocol_key": "p03"},
    )
    assert report.participants == ["ceo", "cfo"]
    assert report.executive_summary == "Summary here."
    assert report.key_findings == ["Finding 1", "Finding 2"]
    assert report.disagreements == ["Disagreement 1"]
    assert report.confidence_score == 4
    assert report.confidence_label_str == "High"
    assert report.synthesis == "Full synthesis text."
    assert report.agent_contributions == []
    assert report.cost_summary == {"total_usd": 0.01}
    assert report.metadata == {"protocol_key": "p03"}


# ── Test: from_envelope ────────────────────────────────────────────────────────

def test_from_envelope(sample_envelope, sample_verdict):
    """from_envelope maps all RunEnvelope fields to ProtocolReport correctly."""
    report = from_envelope(sample_envelope, sample_verdict)

    assert report.participants == ["ceo", "cfo", "cto"]
    assert report.synthesis == SAMPLE_SUMMARY
    assert report.confidence_score == 4
    assert report.confidence_label_str == "High"
    assert report.cost_summary == sample_envelope.cost
    assert report.metadata["protocol_key"] == "p03_parallel_synthesis"
    assert report.metadata["question"] == "Should we expand into Europe?"
    assert report.metadata["trace_id"] == "trace-abc-123"
    assert report.metadata["run_id"] == 42


def test_from_envelope_executive_summary(sample_envelope, sample_verdict):
    """executive_summary is the first paragraph of result_summary."""
    report = from_envelope(sample_envelope, sample_verdict)
    # SAMPLE_SUMMARY starts with 'This is the executive summary paragraph.'
    assert report.executive_summary == "This is the executive summary paragraph."


def test_from_envelope_key_findings(sample_envelope, sample_verdict):
    """key_findings extracts bullet lines from result_summary."""
    report = from_envelope(sample_envelope, sample_verdict)
    assert "The market opportunity is significant" in report.key_findings
    assert "Revenue growth is projected at 15% YoY" in report.key_findings


def test_from_envelope_disagreements(sample_envelope, sample_verdict):
    """disagreements extracts signal-word sentences from result_summary."""
    report = from_envelope(sample_envelope, sample_verdict)
    assert len(report.disagreements) > 0
    # At least one sentence contains a signal word
    joined = " ".join(report.disagreements).lower()
    assert any(sig in joined for sig in ("however", "contrast", "dissent", "alternative view"))


# ── Test: extract_disagreements ───────────────────────────────────────────────

def test_extract_disagreements_finds_signal_words():
    """extract_disagreements returns sentences containing signal words."""
    text = (
        "All agreed on growth. "
        "However, the CFO raised concerns. "
        "In contrast, the CTO supported expansion. "
        "The team moved forward."
    )
    result = extract_disagreements(text)
    assert len(result) == 2
    assert any("However" in s or "however" in s.lower() for s in result)
    assert any("In contrast" in s or "in contrast" in s.lower() for s in result)


def test_extract_disagreements_caps_at_4():
    """extract_disagreements caps results at 4 even when more signals exist."""
    text = ". ".join([
        "However this is one",
        "However this is two",
        "In contrast this is three",
        "Dissent was noted here",
        "Alternative view was proposed",
        "On the other hand consider this",
    ])
    result = extract_disagreements(text)
    assert len(result) <= 4


def test_extract_disagreements_empty_when_no_signals():
    """extract_disagreements returns empty list when no signal words present."""
    text = "All agents agreed. The team aligned on the recommendation. No issues found."
    result = extract_disagreements(text)
    assert result == []


def test_extract_disagreements_case_insensitive():
    """extract_disagreements is case-insensitive for signal matching."""
    text = "HOWEVER this is uppercase. however lowercase too."
    result = extract_disagreements(text)
    assert len(result) >= 1


# ── Test: extract_key_findings ────────────────────────────────────────────────

def test_extract_key_findings_extracts_bullet_lines():
    """extract_key_findings extracts lines starting with '- ' or '* '."""
    text = "Intro paragraph.\n\n- Finding one\n- Finding two\n* Finding three\n\nConclusion."
    result = extract_key_findings(text)
    assert "Finding one" in result
    assert "Finding two" in result
    assert "Finding three" in result


def test_extract_key_findings_fallback_to_sentences():
    """extract_key_findings falls back to first 3 sentences when no bullets."""
    text = "First sentence. Second sentence. Third sentence. Fourth sentence."
    result = extract_key_findings(text)
    assert len(result) == 3
    assert "First sentence" in result[0]


def test_extract_key_findings_strips_bullet_prefix():
    """extract_key_findings strips the '- ' or '* ' prefix from results."""
    text = "- Clean finding without prefix\n* Another clean finding"
    result = extract_key_findings(text)
    for item in result:
        assert not item.startswith("- ")
        assert not item.startswith("* ")


# ── Test: confidence_label ────────────────────────────────────────────────────

def test_confidence_label_unscored():
    assert confidence_label(0) == "Unscored"


def test_confidence_label_low():
    assert confidence_label(1) == "Low"
    assert confidence_label(2) == "Low"


def test_confidence_label_medium():
    assert confidence_label(3) == "Medium"


def test_confidence_label_high():
    assert confidence_label(4) == "High"
    assert confidence_label(5) == "High"


# ── Test: AgentContribution ───────────────────────────────────────────────────

def test_agent_contributions_excludes_internal_keys(sample_envelope, sample_verdict):
    """from_envelope filters out _synthesis, _result, _stage from contributions."""
    report = from_envelope(sample_envelope, sample_verdict)
    contrib_keys = [c.agent_key for c in report.agent_contributions]
    assert "_synthesis" not in contrib_keys
    assert "_result" not in contrib_keys
    assert "_stage" not in contrib_keys


def test_agent_contributions_includes_real_agents(sample_envelope, sample_verdict):
    """from_envelope includes real agent contributions."""
    report = from_envelope(sample_envelope, sample_verdict)
    contrib_keys = [c.agent_key for c in report.agent_contributions]
    assert "ceo" in contrib_keys
    assert "cfo" in contrib_keys


def test_agent_contribution_fields(sample_envelope, sample_verdict):
    """AgentContribution has all required fields."""
    report = from_envelope(sample_envelope, sample_verdict)
    ceo_contrib = next(c for c in report.agent_contributions if c.agent_key == "ceo")
    assert ceo_contrib.agent_name == "CEO"
    assert ceo_contrib.text == "The strategic opportunity is clear."
    assert ceo_contrib.model == "claude-opus-4-6"
    assert ceo_contrib.cost_usd == 0.01
    assert isinstance(ceo_contrib.tool_calls, list)


# ── Test: from_envelope with no verdict ───────────────────────────────────────

def test_from_envelope_no_verdict(sample_envelope):
    """When judge_verdict is None, confidence_score=0 and confidence_label='Unscored'."""
    report = from_envelope(sample_envelope, None)
    assert report.confidence_score == 0
    assert report.confidence_label_str == "Unscored"


def test_from_envelope_empty_verdict(sample_envelope):
    """When judge_verdict is empty dict, confidence_score=0 and confidence_label='Unscored'."""
    report = from_envelope(sample_envelope, {})
    assert report.confidence_score == 0
    assert report.confidence_label_str == "Unscored"


# ── Test: as_dict ─────────────────────────────────────────────────────────────

def test_as_dict(sample_envelope, sample_verdict):
    """ProtocolReport.as_dict() returns a serializable dict with all fields."""
    import json
    report = from_envelope(sample_envelope, sample_verdict)
    d = report.as_dict()

    # Must be JSON-serializable
    serialized = json.dumps(d)
    assert serialized  # non-empty

    # Must contain all required keys
    required_keys = {
        "participants",
        "executive_summary",
        "key_findings",
        "disagreements",
        "confidence_score",
        "confidence_label",
        "synthesis",
        "agent_contributions",
        "cost_summary",
        "metadata",
    }
    assert required_keys.issubset(set(d.keys()))

    # Agent contributions should be dicts, not AgentContribution objects
    for contrib in d["agent_contributions"]:
        assert isinstance(contrib, dict)
