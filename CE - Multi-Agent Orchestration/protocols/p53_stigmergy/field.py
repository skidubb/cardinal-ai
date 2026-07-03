"""Pure helpers for P53 Stigmergy — no LLM imports.

Split out so unit tests can import parse/decay/harvest without triggering the
litellm/anthropic import cascade. The orchestrator imports from here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


TRACE_TYPES: tuple[str, ...] = (
    "risk",
    "opportunity",
    "constraint",
    "insight",
    "question",
)

DECAY_PER_WAVE: float = 0.6
DEFAULT_WAVES: int = 3
DEFAULT_TOP_N_PER_TYPE: int = 5


@dataclass(slots=True)
class Trace:
    """A single stigmergic trace deposited by one agent."""

    trace_type: str
    location: str
    strength: float
    content: str
    author: str
    wave: int

    def decayed_strength(self, current_wave: int) -> float:
        gap = max(0, current_wave - self.wave)
        return round(self.strength * (DECAY_PER_WAVE ** gap), 4)

    def as_dict(self) -> dict[str, Any]:
        return {
            "trace_type": self.trace_type,
            "location": self.location,
            "strength": self.strength,
            "content": self.content,
            "author": self.author,
            "wave": self.wave,
        }


@dataclass(slots=True)
class LocationSummary:
    """Aggregated traces at one (type, location) point in the field."""

    location: str
    trace_type: str
    cumulative_strength: float
    trace_count: int
    contributors: list[str]
    contents: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "location": self.location,
            "trace_type": self.trace_type,
            "cumulative_strength": round(self.cumulative_strength, 3),
            "trace_count": self.trace_count,
            "contributors": self.contributors,
            "contents": self.contents,
        }


@dataclass(slots=True)
class StigmergyResult:
    """The emergent trace field grouped by type."""

    question: str
    waves: int
    agents: list[str]
    all_traces: list[Trace] = field(default_factory=list)
    by_type: dict[str, list[LocationSummary]] = field(default_factory=dict)
    unreacheable_agents: list[str] = field(default_factory=list)
    synthesis: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "waves": self.waves,
            "agents": self.agents,
            "all_traces": [t.as_dict() for t in self.all_traces],
            "by_type": {
                t: [s.as_dict() for s in summaries]
                for t, summaries in self.by_type.items()
            },
            "unreacheable_agents": self.unreacheable_agents,
            "synthesis": self.synthesis,
        }


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_traces(text: str, *, author: str, wave: int) -> list[Trace]:
    """Parse a JSON array of trace dicts into `Trace` objects. Never raises."""
    try:
        data = _extract_json_array(text)
    except ValueError:
        return []

    traces: list[Trace] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        trace_type = str(item.get("type", "")).strip().lower()
        location = str(item.get("location", "")).strip().lower()
        content = str(item.get("content", "")).strip()
        try:
            strength = float(item.get("strength", 0.0))
        except (TypeError, ValueError):
            continue
        strength = max(0.0, min(1.0, strength))
        if not trace_type or not location or not content or strength == 0.0:
            continue
        if trace_type not in TRACE_TYPES:
            continue
        traces.append(
            Trace(
                trace_type=trace_type,
                location=location,
                strength=strength,
                content=content,
                author=author,
                wave=wave,
            )
        )
    return traces


def _extract_json_array(text: str) -> list[Any]:
    """Best-effort extractor: handles markdown fences and prose."""
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("no JSON array found")
    try:
        parsed = json.loads(text[start : end + 1])
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass
    raise ValueError("could not parse JSON array")


# ---------------------------------------------------------------------------
# Rendering + harvesting — pure mechanical, no LLM
# ---------------------------------------------------------------------------

def _summarize_locations(
    traces: list[Trace],
    *,
    current_wave: int,
) -> list[LocationSummary]:
    grouped: dict[tuple[str, str], list[Trace]] = {}
    for t in traces:
        grouped.setdefault((t.trace_type, t.location), []).append(t)

    summaries: list[LocationSummary] = []
    for (trace_type, location), bucket in grouped.items():
        cumulative = sum(t.decayed_strength(current_wave) for t in bucket)
        summaries.append(
            LocationSummary(
                location=location,
                trace_type=trace_type,
                cumulative_strength=cumulative,
                trace_count=len(bucket),
                contributors=sorted({t.author for t in bucket}),
                contents=[t.content for t in bucket],
            )
        )
    return summaries


def format_trace_field(traces: list[Trace], *, current_wave: int, top_n: int = 20) -> str:
    """Render the current (decayed) trace field as a compact prompt block."""
    if not traces:
        return "(no traces yet — the field is empty)"
    summaries = _summarize_locations(traces, current_wave=current_wave)
    ranked = sorted(summaries, key=lambda s: s.cumulative_strength, reverse=True)[:top_n]
    lines = []
    for s in ranked:
        contents = "; ".join(s.contents[:3])
        lines.append(
            f"  [{s.trace_type}] {s.location} "
            f"(strength={round(s.cumulative_strength, 2)}, n={s.trace_count}): {contents}"
        )
    return "\n".join(lines)


def harvest_field(
    traces: list[Trace],
    *,
    top_n_per_type: int = DEFAULT_TOP_N_PER_TYPE,
    harvest_wave: int | None = None,
) -> dict[str, list[LocationSummary]]:
    """Group + rank the trace field. Mechanical, no LLM."""
    if not traces:
        return {t: [] for t in TRACE_TYPES}

    max_wave = harvest_wave if harvest_wave is not None else max(t.wave for t in traces)
    summaries = _summarize_locations(traces, current_wave=max_wave)

    by_type: dict[str, list[LocationSummary]] = {t: [] for t in TRACE_TYPES}
    for s in summaries:
        by_type.setdefault(s.trace_type, []).append(s)

    for trace_type, bucket in by_type.items():
        bucket.sort(key=lambda s: s.cumulative_strength, reverse=True)
        by_type[trace_type] = bucket[:top_n_per_type]

    return by_type
