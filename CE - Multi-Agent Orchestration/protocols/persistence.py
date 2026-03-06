"""Persist protocol run envelopes to Postgres via ce-db.

Unlike the previous best-effort no-op behavior, this module reports explicit
telemetry degradation warnings in-band through ``PersistOutcome``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from protocols.run_envelope import RunEnvelope, build_run_envelope

_log = logging.getLogger(__name__)


@dataclass(slots=True)
class PersistOutcome:
    """Result of a persistence attempt."""

    run_id: str | None = None
    persisted: bool = False
    warnings: list[dict[str, Any]] = field(default_factory=list)

    @property
    def telemetry_degraded(self) -> bool:
        return len(self.warnings) > 0


def _warning(code: str, message: str, recoverable: bool = True) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "component": "postgres_persistence",
        "recoverable": recoverable,
    }


def _cost_totals(cost_summary: dict[str, Any]) -> tuple[float, int, int]:
    total_cost = float(cost_summary.get("total_usd", 0.0) or 0.0)
    total_input = 0
    total_output = 0

    by_model = cost_summary.get("by_model", {})
    if isinstance(by_model, dict) and by_model:
        for model_data in by_model.values():
            total_input += int(model_data.get("input_tokens", 0) or 0)
            total_output += int(model_data.get("output_tokens", 0) or 0)
        return total_cost, total_input, total_output

    by_agent = cost_summary.get("by_agent", {})
    if isinstance(by_agent, dict):
        for agent_data in by_agent.values():
            total_input += int(agent_data.get("input_tokens", 0) or 0)
            total_output += int(agent_data.get("output_tokens", 0) or 0)

    return total_cost, total_input, total_output


async def persist_run(
    protocol_key: str,
    question: str,
    agent_keys: list[str],
    result: Any,
    cost_tracker: Any | None = None,
    trace_id: str | None = None,
    source: str = "cli",
    started_at: datetime | None = None,
    error: str | None = None,
    envelope: RunEnvelope | None = None,
) -> PersistOutcome:
    """Persist a protocol run to Postgres and return structured outcome info."""
    outcome = PersistOutcome()
    implicit_tracker_used = False

    if envelope is None:
        if cost_tracker is None:
            try:
                from protocols.llm import get_cost_tracker

                cost_tracker = get_cost_tracker()
                implicit_tracker_used = cost_tracker is not None
            except Exception:
                cost_tracker = None

        cost_summary: dict[str, Any] | None = None
        if cost_tracker is not None:
            try:
                cost_summary = cost_tracker.summary()
            except Exception:
                _log.debug("Cost tracker summary failed", exc_info=True)

        envelope = build_run_envelope(
            protocol_key=protocol_key,
            question=question,
            agent_keys=agent_keys,
            result=result,
            source=source,
            status="failed" if error else "completed",
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            trace_id=trace_id,
            cost_summary=cost_summary,
        )
        if error:
            envelope.result_json["error_message"] = error[:4000]

    try:
        from ce_db import AgentOutput, Run, get_session
    except ImportError:
        msg = "ce-db is not importable; run persisted only in local runtime surfaces."
        _log.warning(msg)
        outcome.warnings.append(_warning("ce_db_unavailable", msg))
        return outcome

    total_cost, total_input, total_output = _cost_totals(envelope.cost)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start = envelope.started_at.replace(tzinfo=None) if envelope.started_at.tzinfo else envelope.started_at

    try:
        async with get_session() as session:
            run = Run(
                protocol_key=envelope.protocol_key,
                question=envelope.question,
                agent_keys=envelope.agent_keys,
                source=envelope.source,
                status=envelope.status,
                result_json=envelope.as_dict(),
                result_summary=envelope.result_summary,
                total_cost_usd=total_cost,
                total_input_tokens=total_input,
                total_output_tokens=total_output,
                langfuse_trace_id=envelope.trace_id or trace_id,
                error_message=error[:4000] if error else None,
                started_at=start or now,
                completed_at=now,
            )
            session.add(run)
            await session.flush()

            for ao in envelope.agent_outputs:
                session.add(
                    AgentOutput(
                        run_id=run.id,
                        agent_key=ao.agent_key or "",
                        round_number=ao.round_number,
                        output_text=ao.text[:10_000],
                        cost_usd=ao.cost_usd,
                        input_tokens=ao.input_tokens,
                        output_tokens=ao.output_tokens,
                        model=ao.model or None,
                        started_at=ao.started_at.replace(tzinfo=None)
                        if ao.started_at and ao.started_at.tzinfo
                        else ao.started_at,
                        completed_at=ao.completed_at.replace(tzinfo=None)
                        if ao.completed_at and ao.completed_at.tzinfo
                        else ao.completed_at,
                    )
                )

            outcome.run_id = str(run.id)
            outcome.persisted = True
            _log.info("Persisted run %s for %s", outcome.run_id, envelope.protocol_key)
            return outcome

    except Exception as e:
        msg = f"Postgres persistence failed: {e}"
        _log.warning(msg)
        outcome.warnings.append(_warning("postgres_write_failed", msg))
        return outcome
    finally:
        if implicit_tracker_used:
            try:
                from protocols.llm import set_cost_tracker

                set_cost_tracker(None)
            except Exception:
                _log.debug("Failed to clear implicit tracker", exc_info=True)
