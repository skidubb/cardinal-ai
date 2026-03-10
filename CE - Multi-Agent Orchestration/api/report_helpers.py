"""Helpers for reconstructing RunEnvelope from DB records.

Used by the GET /api/runs/{id} endpoint to build a ProtocolReport
from a previously completed run stored in SQLite.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from api.models import AgentOutput, Run
from protocols.run_envelope import AgentOutputEnvelope, RunEnvelope


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def build_envelope_from_db(run: Run, session: Session) -> RunEnvelope:
    """Reconstruct a RunEnvelope from a Run record and its AgentOutput rows.

    Args:
        run: The Run SQLModel row.
        session: Active SQLModel session for querying AgentOutput rows.

    Returns:
        RunEnvelope populated from DB data. result_summary is taken from the
        _synthesis AgentOutput row if present. All other agent outputs are
        included as AgentOutputEnvelope instances.
    """
    agent_output_rows = list(
        session.exec(select(AgentOutput).where(AgentOutput.run_id == run.id)).all()
    )

    result_summary = ""
    agent_outputs: list[AgentOutputEnvelope] = []

    for row in agent_output_rows:
        if row.agent_key == "_synthesis":
            result_summary = row.output_text
            continue

        tool_calls: list[dict[str, Any]] = []
        if row.tool_calls_json and row.tool_calls_json != "[]":
            try:
                tool_calls = json.loads(row.tool_calls_json)
            except (json.JSONDecodeError, ValueError):
                tool_calls = []

        agent_outputs.append(
            AgentOutputEnvelope(
                agent_key=row.agent_key,
                agent_name=row.agent_key,  # name not stored separately; key is sufficient
                text=row.output_text,
                model=row.model,
                input_tokens=row.input_tokens,
                output_tokens=row.output_tokens,
                cost_usd=row.cost_usd,
                started_at=row.started_at,
                completed_at=row.completed_at,
                tool_calls=tool_calls,
            )
        )

    # Reconstruct cost summary from totals stored on Run
    cost_summary: dict[str, Any] = {
        "total_usd": run.cost_usd,
        "calls": len(agent_outputs),
        "by_model": {},
    }

    # Infer agent_keys from stored outputs (excluding internal keys)
    _internal = frozenset(("_synthesis", "_result", "_stage"))
    raw_agent_keys = [o.agent_key for o in agent_outputs if o.agent_key not in _internal]

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_agent_keys: list[str] = []
    for key in raw_agent_keys:
        if key not in seen:
            seen.add(key)
            unique_agent_keys.append(key)

    started = run.started_at or _utc_now()
    completed = run.completed_at or started

    return RunEnvelope(
        protocol_key=run.protocol_key or "",
        question=run.question or "",
        agent_keys=unique_agent_keys,
        source="db",
        status=run.status or "completed",
        started_at=started,
        completed_at=completed,
        result_json={},
        result_summary=result_summary,
        cost=cost_summary,
        trace_id=run.trace_id,
        run_id=run.id,
        agent_outputs=agent_outputs,
    )
