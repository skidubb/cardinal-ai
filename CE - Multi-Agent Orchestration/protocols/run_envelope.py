"""Canonical run envelope for protocol execution telemetry and persistence.

This module is the single extraction + normalization boundary between
protocol result objects and storage/streaming layers.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

MAX_TEXT_LEN = 10_000
MAX_RESULT_STR_LEN = 5_000


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _trim_text(value: Any, max_len: int = MAX_TEXT_LEN) -> str:
    text = value if isinstance(value, str) else str(value)
    return text[:max_len]


def _to_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _normalize_agent_token(value: str) -> str:
    return value.strip().lower().replace("_", "-").replace(" ", "-")


@dataclass(slots=True)
class TelemetryWarning:
    """In-band warning that describes telemetry degradation."""

    code: str
    message: str
    component: str = "telemetry"
    level: str = "warning"
    recoverable: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "component": self.component,
            "level": self.level,
            "recoverable": self.recoverable,
        }


@dataclass(slots=True)
class AgentOutputEnvelope:
    """Normalized per-agent output unit."""

    agent_key: str
    text: str
    agent_name: str = ""
    round_number: int = 0
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "agent_key": self.agent_key,
            "agent_name": self.agent_name,
            "text": self.text,
            "round_number": self.round_number,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": self.cost_usd,
            "started_at": _to_iso(self.started_at),
            "completed_at": _to_iso(self.completed_at),
            "tool_calls": self.tool_calls,
            "metadata": self.metadata,
        }

    def as_sse_payload(self) -> dict[str, Any]:
        payload = {
            "agent_key": self.agent_key,
            "agent_name": self.agent_name,
            "text": self.text,
        }
        if self.round_number:
            payload["round"] = self.round_number
        if self.cost_usd:
            payload["cost_usd"] = self.cost_usd
        return payload


@dataclass(slots=True)
class StepEnvelope:
    """Normalized per-step envelope for pipeline runs."""

    step_order: int
    protocol_key: str
    status: str
    question: str = ""
    synthesis: str = ""
    cost: dict[str, Any] = field(default_factory=dict)
    agent_outputs: list[AgentOutputEnvelope] = field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "step_order": self.step_order,
            "protocol_key": self.protocol_key,
            "status": self.status,
            "question": self.question,
            "synthesis": self.synthesis,
            "cost": self.cost,
            "agent_outputs": [o.as_dict() for o in self.agent_outputs],
            "started_at": _to_iso(self.started_at),
            "completed_at": _to_iso(self.completed_at),
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class RunEnvelope:
    """Canonical run representation for persistence and replay."""

    protocol_key: str
    question: str
    agent_keys: list[str]
    source: str
    status: str
    started_at: datetime
    completed_at: datetime
    result_json: dict[str, Any]
    result_summary: str
    cost: dict[str, Any] = field(default_factory=dict)
    trace_id: str | None = None
    run_id: str | int | None = None
    agent_outputs: list[AgentOutputEnvelope] = field(default_factory=list)
    steps: list[StepEnvelope] = field(default_factory=list)
    attachments: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[TelemetryWarning] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def telemetry_degraded(self) -> bool:
        return len(self.warnings) > 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "protocol_key": self.protocol_key,
            "question": self.question,
            "agent_keys": self.agent_keys,
            "source": self.source,
            "status": self.status,
            "started_at": _to_iso(self.started_at),
            "completed_at": _to_iso(self.completed_at),
            "trace_id": self.trace_id,
            "result_summary": self.result_summary,
            "result_json": self.result_json,
            "cost": self.cost,
            "agent_outputs": [o.as_dict() for o in self.agent_outputs],
            "steps": [s.as_dict() for s in self.steps],
            "attachments": self.attachments,
            "warnings": [w.as_dict() for w in self.warnings],
            "metadata": self.metadata,
        }

    def add_warning(self, warning: TelemetryWarning | dict[str, Any]) -> None:
        self.warnings.append(_coerce_warning(warning))


def _coerce_warning(warning: TelemetryWarning | dict[str, Any]) -> TelemetryWarning:
    if isinstance(warning, TelemetryWarning):
        return warning
    return TelemetryWarning(
        code=str(warning.get("code", "telemetry_warning")),
        message=str(warning.get("message", "Telemetry warning")),
        component=str(warning.get("component", "telemetry")),
        level=str(warning.get("level", "warning")),
        recoverable=bool(warning.get("recoverable", True)),
    )


def _result_to_dict(result: Any) -> dict[str, Any]:
    if dataclasses.is_dataclass(result) and not isinstance(result, type):
        return dataclasses.asdict(result)
    if isinstance(result, dict):
        return result
    if hasattr(result, "__dict__"):
        return {k: _trim_text(v, MAX_RESULT_STR_LEN) for k, v in result.__dict__.items()}
    return {"raw": _trim_text(result, MAX_RESULT_STR_LEN)}


def extract_synthesis(result: Any) -> str:
    """Extract a concise synthesis from common result shapes."""
    for attr in ("synthesis", "final_synthesis", "final_output", "recommendation", "summary", "conclusion"):
        val = getattr(result, attr, None)
        if isinstance(val, str) and val.strip():
            return _trim_text(val, 2_000)

    if isinstance(result, dict):
        for key in ("synthesis", "final_synthesis", "final_output", "recommendation", "summary", "conclusion"):
            val = result.get(key)
            if isinstance(val, str) and val.strip():
                return _trim_text(val, 2_000)

    return ""


def name_to_key(name: str, agent_keys: list[str]) -> str:
    token = _normalize_agent_token(name)
    for key in agent_keys:
        key_token = _normalize_agent_token(key)
        if key_token and (key_token in token or token in key_token):
            return key
    return token


def _value_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return str(value)


def _output_from_item(item: Any, agent_keys: list[str], round_number: int = 0) -> AgentOutputEnvelope | None:
    if isinstance(item, dict):
        name = str(
            item.get("agent_name")
            or item.get("name")
            or item.get("agent")
            or item.get("role")
            or ""
        )
        text_val = (
            item.get("text")
            or item.get("response")
            or item.get("output")
            or item.get("content")
            or item.get("analysis")
            or item.get("argument")
            or item.get("reasoning")
        )
        if text_val is None:
            return None
        return AgentOutputEnvelope(
            agent_key=item.get("agent_key") or name_to_key(name, agent_keys),
            agent_name=name,
            text=_trim_text(_value_text(text_val)),
            round_number=int(item.get("round") or round_number or 0),
        )

    name = getattr(item, "agent_name", None) or getattr(item, "name", None) or getattr(item, "agent", None) or ""
    for attr in ("text", "response", "output", "content", "analysis", "argument", "reasoning"):
        val = getattr(item, attr, None)
        if val is not None:
            return AgentOutputEnvelope(
                agent_key=name_to_key(str(name), agent_keys),
                agent_name=str(name),
                text=_trim_text(_value_text(val)),
                round_number=round_number,
            )
    return None


def extract_agent_outputs(result: Any, agent_keys: list[str]) -> list[AgentOutputEnvelope]:
    """Extract normalized agent outputs from protocol results."""
    outputs: list[AgentOutputEnvelope] = []

    def add_once(candidate: AgentOutputEnvelope | None) -> None:
        if candidate is None:
            return
        sig = (
            candidate.agent_key,
            candidate.round_number,
            candidate.text[:200],
        )
        if sig in seen:
            return
        seen.add(sig)
        outputs.append(candidate)

    seen: set[tuple[str, int, str]] = set()

    # P03-style
    if hasattr(result, "perspectives") and isinstance(result.perspectives, list):
        for p in result.perspectives:
            add_once(_output_from_item(p, agent_keys))
        if outputs:
            return outputs

    # P04 / Delphi-style rounds
    if hasattr(result, "rounds") and isinstance(result.rounds, list):
        for idx, rnd in enumerate(result.rounds, start=1):
            for attr in ("responses", "arguments", "estimates", "votes"):
                lst = getattr(rnd, attr, None)
                if isinstance(lst, list):
                    for item in lst:
                        add_once(_output_from_item(item, agent_keys, round_number=idx))
            add_once(_output_from_item(rnd, agent_keys, round_number=idx))
        if outputs:
            return outputs

    # TRIZ-style
    if hasattr(result, "agent_contributions") and isinstance(result.agent_contributions, dict):
        for name, text in result.agent_contributions.items():
            add_once(
                AgentOutputEnvelope(
                    agent_key=name_to_key(str(name), agent_keys),
                    agent_name=str(name),
                    text=_trim_text(_value_text(text)),
                )
            )
        if outputs:
            return outputs

    # Stage-heavy outputs
    if hasattr(result, "stages") and isinstance(result.stages, list):
        for stage in result.stages:
            stage_name = getattr(stage, "name", "") or getattr(stage, "stage", "") or "stage"
            stage_text = getattr(stage, "output", None) or getattr(stage, "text", None) or str(stage)
            add_once(
                AgentOutputEnvelope(
                    agent_key="_stage",
                    agent_name=str(stage_name),
                    text=_trim_text(_value_text(stage_text)),
                )
            )
        if outputs:
            return outputs

    # Generic list containers seen across protocols
    for attr in ("agent_outputs", "responses", "agent_responses", "arguments", "contributions"):
        val = getattr(result, attr, None)
        if isinstance(val, list):
            for item in val:
                add_once(_output_from_item(item, agent_keys))
            if outputs:
                return outputs

    # Dict fallback for results that store contributions under custom keys
    if isinstance(result, dict):
        for key, val in result.items():
            if isinstance(val, list):
                for item in val:
                    add_once(_output_from_item(item, agent_keys))
            elif isinstance(val, dict) and "agent" in val and ("text" in val or "response" in val):
                add_once(_output_from_item(val, agent_keys))
        if outputs:
            return outputs

    # Always emit at least one output row so downstream diffs/evals are never empty.
    outputs.append(
        AgentOutputEnvelope(
            agent_key="_result",
            agent_name="Result",
            text=_trim_text(result, MAX_RESULT_STR_LEN),
        )
    )
    return outputs


def attach_tool_events(
    outputs: list[AgentOutputEnvelope],
    tool_events: list[dict[str, Any]],
    agent_keys: list[str],
) -> None:
    """Attach tool events to agent output records."""
    by_agent: dict[str, list[dict[str, Any]]] = {}
    for evt in tool_events:
        evt_agent = str(evt.get("agent_name") or "")
        if not evt_agent:
            continue
        norm = _normalize_agent_token(evt_agent)
        by_agent.setdefault(norm, []).append(
            {
                "event": evt.get("event"),
                "tool_name": evt.get("tool_name"),
                "tool_input": evt.get("tool_input"),
                "result_preview": evt.get("result_preview"),
                "elapsed_ms": evt.get("elapsed_ms"),
                "iteration": evt.get("iteration"),
            }
        )

    for out in outputs:
        tokens = {
            _normalize_agent_token(out.agent_name),
            _normalize_agent_token(out.agent_key),
        }
        tokens.add(_normalize_agent_token(name_to_key(out.agent_name or out.agent_key, agent_keys)))
        matched: list[dict[str, Any]] = []
        for token in tokens:
            if token and token in by_agent:
                matched.extend(by_agent[token])
        out.tool_calls = matched


def attach_cost_summary(outputs: list[AgentOutputEnvelope], cost_summary: dict[str, Any], agent_keys: list[str]) -> None:
    """Attach aggregated per-agent usage/cost where available."""
    by_agent = cost_summary.get("by_agent", {})
    if not isinstance(by_agent, dict) or not by_agent:
        return

    used_agent_keys: set[str] = set()

    for out in outputs:
        key_candidates = {
            _normalize_agent_token(out.agent_name),
            _normalize_agent_token(out.agent_key),
            _normalize_agent_token(name_to_key(out.agent_name or out.agent_key, agent_keys)),
        }

        stats: dict[str, Any] | None = None
        matched_key = ""
        for candidate in key_candidates:
            if not candidate:
                continue
            if candidate in by_agent:
                stats = by_agent[candidate]
                matched_key = candidate
                break
            for agg_key, agg_stats in by_agent.items():
                if candidate in agg_key or agg_key in candidate:
                    stats = agg_stats
                    matched_key = agg_key
                    break
            if stats is not None:
                break

        if not stats or matched_key in used_agent_keys:
            continue

        used_agent_keys.add(matched_key)
        out.input_tokens = int(stats.get("input_tokens", 0))
        out.output_tokens = int(stats.get("output_tokens", 0))
        out.cost_usd = float(stats.get("cost_usd", 0.0))
        if not out.model:
            out.model = str(stats.get("primary_model", ""))


def build_run_envelope(
    *,
    protocol_key: str,
    question: str,
    agent_keys: list[str],
    result: Any,
    source: str = "cli",
    status: str = "completed",
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    trace_id: str | None = None,
    run_id: str | int | None = None,
    cost_summary: dict[str, Any] | None = None,
    tool_events: list[dict[str, Any]] | None = None,
    steps: list[StepEnvelope] | None = None,
    attachments: list[dict[str, Any]] | None = None,
    warnings: list[TelemetryWarning | dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> RunEnvelope:
    """Build a canonical run envelope from a protocol result."""
    result_dict = _result_to_dict(result)
    outputs = extract_agent_outputs(result, agent_keys)

    if tool_events:
        attach_tool_events(outputs, tool_events, agent_keys)
    if cost_summary:
        attach_cost_summary(outputs, cost_summary, agent_keys)

    envelope = RunEnvelope(
        protocol_key=protocol_key,
        question=question,
        agent_keys=list(agent_keys),
        source=source,
        status=status,
        started_at=started_at or _utc_now(),
        completed_at=completed_at or _utc_now(),
        trace_id=trace_id,
        run_id=run_id,
        result_json=result_dict,
        result_summary=extract_synthesis(result) or extract_synthesis(result_dict),
        cost=cost_summary or {"total_usd": 0.0, "calls": 0, "by_model": {}},
        agent_outputs=outputs,
        steps=steps or [],
        attachments=attachments or [],
        metadata=metadata or {},
    )

    if warnings:
        for warning in warnings:
            envelope.add_warning(warning)

    return envelope
