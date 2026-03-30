"""ProtocolReport dataclass and from_envelope transform.

This module defines the canonical structured report output for any protocol run.
It depends only on protocols/run_envelope.py — no api/ imports allowed.

Usage:
    from protocols.protocol_report import ProtocolReport, from_envelope
    report = from_envelope(envelope, judge_verdict_dict)
    response["protocol_report"] = report.as_dict()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from protocols.run_envelope import RunEnvelope


# ── Constants ─────────────────────────────────────────────────────────────────

DISAGREEMENT_SIGNALS = (
    "however",
    "disagree",
    "contrary",
    "alternative view",
    "dissent",
    "in contrast",
    "on the other hand",
)

_INTERNAL_AGENT_KEYS = frozenset(("_synthesis", "_result", "_stage"))


# ── Helper functions ──────────────────────────────────────────────────────────

def extract_disagreements(text: str) -> list[str]:
    """Extract sentences containing disagreement signal words.

    Splits on '. ' boundaries, filters by signal word presence (case-insensitive),
    and caps results at 4.

    Args:
        text: Source text to scan for disagreements.

    Returns:
        List of disagreement sentences, capped at 4.
    """
    # Split on '. ' to get sentence fragments; also handle '\n' sentence starts
    raw_sentences: list[str] = []
    for part in text.split(". "):
        for sub in part.split("\n"):
            stripped = sub.strip()
            if stripped:
                raw_sentences.append(stripped)

    found: list[str] = []
    for sentence in raw_sentences:
        lower = sentence.lower()
        if any(signal in lower for signal in DISAGREEMENT_SIGNALS):
            found.append(sentence)
            if len(found) >= 4:
                break

    return found


def extract_key_findings(text: str) -> list[str]:
    """Extract key findings from structured text.

    Extracts lines starting with '- ' or '* ' (bullet list items).
    Falls back to the first 3 sentences if no bullet lines found.

    Args:
        text: Source text to extract findings from.

    Returns:
        List of finding strings (without bullet prefixes).
    """
    lines = text.split("\n")
    bullet_findings: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- ") or stripped.startswith("* "):
            bullet_findings.append(stripped[2:].strip())

    if bullet_findings:
        return bullet_findings

    # Fallback: first 3 sentences
    sentences: list[str] = []
    for raw in text.split(". "):
        s = raw.strip()
        if s:
            sentences.append(s)
        if len(sentences) >= 3:
            break
    return sentences


def confidence_label(score: int) -> str:
    """Map a numeric confidence score (0-5) to a human-readable label.

    Args:
        score: Integer confidence score from JudgeVerdict.overall. 0 = unscored.

    Returns:
        "Unscored", "Low", "Medium", or "High".
    """
    if score == 0:
        return "Unscored"
    if score <= 2:
        return "Low"
    if score == 3:
        return "Medium"
    return "High"


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class AgentContribution:
    """Normalized per-agent contribution within a ProtocolReport."""

    agent_key: str
    agent_name: str
    text: str
    cost_usd: float = 0.0
    model: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "agent_key": self.agent_key,
            "agent_name": self.agent_name,
            "text": self.text,
            "cost_usd": self.cost_usd,
            "model": self.model,
            "tool_calls": self.tool_calls,
        }


@dataclass
class ProtocolReport:
    """Structured report produced from a completed protocol run.

    This is the canonical data model consumed by all downstream presentation
    layers (browser view, PDF export, shareable URL).

    All fields are plain Python types (str, int, list, dict) to ensure
    JSON serializability via as_dict().
    """

    participants: list[str]
    executive_summary: str
    key_findings: list[str]
    disagreements: list[str]
    confidence_score: int
    confidence_label_str: str
    synthesis: str
    agent_contributions: list[AgentContribution]
    cost_summary: dict[str, Any]
    metadata: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        """Return a fully serializable dict representation."""
        return {
            "participants": self.participants,
            "executive_summary": self.executive_summary,
            "key_findings": self.key_findings,
            "disagreements": self.disagreements,
            "confidence_score": self.confidence_score,
            "confidence_label": self.confidence_label_str,
            "synthesis": self.synthesis,
            "agent_contributions": [c.as_dict() for c in self.agent_contributions],
            "cost_summary": self.cost_summary,
            "metadata": self.metadata,
        }


# ── Transform ─────────────────────────────────────────────────────────────────

def from_envelope(
    envelope: RunEnvelope,
    judge_verdict: dict[str, Any] | None = None,
) -> ProtocolReport:
    """Build a ProtocolReport from a RunEnvelope and optional JudgeVerdict dict.

    Args:
        envelope: Completed RunEnvelope from a protocol execution.
        judge_verdict: Serialized JudgeVerdict dict (from verdict.as_dict()),
                       or None/empty dict if the judge did not run.

    Returns:
        ProtocolReport with all fields populated.
    """
    summary = envelope.result_summary or ""

    # Executive summary: first paragraph (split on double newline)
    paragraphs = [p.strip() for p in summary.split("\n\n") if p.strip()]
    executive_summary = paragraphs[0] if paragraphs else summary

    # Confidence from judge verdict
    score = 0
    if judge_verdict:
        score = int(judge_verdict.get("overall", 0) or 0)

    # Agent contributions — exclude internal keys
    contributions: list[AgentContribution] = []
    for out in envelope.agent_outputs:
        if out.agent_key in _INTERNAL_AGENT_KEYS:
            continue
        contributions.append(
            AgentContribution(
                agent_key=out.agent_key,
                agent_name=out.agent_name,
                text=out.text,
                cost_usd=out.cost_usd,
                model=out.model,
                tool_calls=list(out.tool_calls) if out.tool_calls else [],
            )
        )

    # Metadata
    def _iso(dt: Any) -> str | None:
        if dt is None:
            return None
        return dt.isoformat() if hasattr(dt, "isoformat") else str(dt)

    metadata: dict[str, Any] = {
        "protocol_key": envelope.protocol_key,
        "question": envelope.question,
        "trace_id": envelope.trace_id,
        "run_id": envelope.run_id,
        "started_at": _iso(envelope.started_at),
        "completed_at": _iso(envelope.completed_at),
    }

    return ProtocolReport(
        participants=list(envelope.agent_keys),
        executive_summary=executive_summary,
        key_findings=extract_key_findings(summary),
        disagreements=extract_disagreements(summary),
        confidence_score=score,
        confidence_label_str=confidence_label(score),
        synthesis=summary,
        agent_contributions=contributions,
        cost_summary=dict(envelope.cost),
        metadata=metadata,
    )
