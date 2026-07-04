"""Persist protocol run envelopes to Postgres via ce-db.

Unlike the previous best-effort no-op behavior, this module reports explicit
telemetry degradation warnings in-band through ``PersistOutcome``.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from protocols.run_envelope import RunEnvelope, build_run_envelope


def _default_tenant_slug() -> str:
    """Return the CLI default tenant, respecting CE_ALLOW_PROD opt-in.

    Resolved at call time (not import time) so late .env loads are honored.
    Unauth'd CLI runs default to ``local-dev`` unless ``CE_ALLOW_PROD=1``.
    """
    if os.environ.get("CE_ALLOW_PROD") == "1":
        return "cardinal-element"
    return os.environ.get("CE_DEV_TENANT") or "local-dev"

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


# DUAL_WRITE_DEBT: this helper exists because the portal UI reads from the
# old SQLModel `run` table while `persist_run()` was designed for the new
# ce-db `runs` table. Delete this function (and the `also_write_legacy`
# param on `persist_run`) once the UI is migrated to read from `runs`.
# See CE - Multi-Agent Orchestration/docs/schema.md#migration-debt.
def _write_legacy_run(
    envelope: RunEnvelope,
    tenant_slug: str,
    trace_id: str | None,
    total_cost: float,
    error: str | None,
) -> dict[str, Any] | None:
    """Write the same run to the old SQLModel ``run`` table (UI source of truth).

    Best-effort: if the legacy engine can't be imported, the target table
    doesn't exist, or the insert fails, returns a warning dict and the caller
    attaches it to ``PersistOutcome.warnings``. Never raises.

    This is what makes CLI runs show up in the portal's ``/api/runs``
    endpoint — the UI reads the ``run`` (singular) SQLModel table, not the
    ce-db ``runs`` (plural) Alembic table. See docs/schema.md.
    """
    import json as _json

    try:
        from sqlmodel import Session as _SQLModelSession

        from api.database import engine as _legacy_engine
        from api.models import AgentOutput as _LegacyAO
        from api.models import Run as _LegacyRun
    except Exception as e:
        return _warning(
            "legacy_ui_schema_unavailable",
            f"Legacy run-table write skipped: {type(e).__name__}: {e}. "
            "CLI runs won't appear in the portal until api.database is importable.",
        )

    try:
        # Legacy Run.started_at / completed_at are tz-aware on the API path
        # but tz-naive datetimes work too; Postgres stores TIMESTAMP WITHOUT
        # TIME ZONE on both tables.
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        started_naive = (
            envelope.started_at.replace(tzinfo=None)
            if envelope.started_at and envelope.started_at.tzinfo
            else (envelope.started_at or now)
        )
        completed_naive = (
            envelope.completed_at.replace(tzinfo=None)
            if envelope.completed_at and envelope.completed_at.tzinfo
            else (envelope.completed_at or now)
        )

        with _SQLModelSession(_legacy_engine) as session:
            legacy_run = _LegacyRun(
                type="single",
                protocol_key=envelope.protocol_key,
                question=envelope.question,
                tenant_slug=tenant_slug,
                status=envelope.status,
                cost_usd=float(total_cost or 0.0),
                trace_id=envelope.trace_id or trace_id,
                error_message=(error[:4000] if error else None),
                started_at=started_naive,
                completed_at=completed_naive,
                judge_verdict_json="{}",
                context_mode=None,
                context_files_json="[]",
                agent_keys_json=_json.dumps(envelope.agent_keys or []),
                steps_json="[]",
            )
            session.add(legacy_run)
            session.commit()
            session.refresh(legacy_run)
            legacy_run_id = legacy_run.id

            for ao in envelope.agent_outputs:
                ao_started = (
                    ao.started_at.replace(tzinfo=None)
                    if ao.started_at and ao.started_at.tzinfo
                    else ao.started_at
                )
                ao_completed = (
                    ao.completed_at.replace(tzinfo=None)
                    if ao.completed_at and ao.completed_at.tzinfo
                    else ao.completed_at
                )
                session.add(
                    _LegacyAO(
                        run_id=legacy_run_id,
                        agent_key=ao.agent_key or "",
                        model=ao.model or "",
                        output_text=(ao.text or "")[:10_000],
                        tool_calls_json="[]",
                        input_tokens=ao.input_tokens or 0,
                        output_tokens=ao.output_tokens or 0,
                        cost_usd=float(ao.cost_usd or 0.0),
                        started_at=ao_started,
                        completed_at=ao_completed,
                    )
                )
            session.commit()
        _log.info(
            "Legacy run row %s written for %s (UI will show it)",
            legacy_run_id,
            envelope.protocol_key,
        )
        return None
    except Exception as e:
        msg = f"Legacy run-table write failed: {type(e).__name__}: {e}"
        _log.warning(msg)
        return _warning("legacy_ui_write_failed", msg)


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
    tenant_slug: str | None = None,
    also_write_legacy: bool = True,
) -> PersistOutcome:
    """Persist a protocol run to Postgres and return structured outcome info.

    When ``tenant_slug`` is None (the typical CLI path), it is resolved via
    ``_default_tenant_slug()`` -- ``local-dev`` by default, ``cardinal-element``
    only if ``CE_ALLOW_PROD=1`` is set (Railway does; local dev does not).
    This prevents unauth'd CLI runs from silently writing to production state.
    API callers always pass an explicit slug derived from the caller's auth
    context via ``resolve_tenant`` and are unaffected.

    ``also_write_legacy`` controls the dual-write to the old ``run`` table
    (``api/database.py`` SQLModel schema). The old table is what powers the
    portal UI's ``/api/runs`` endpoint. API callers write to ``run`` themselves
    via ``api/runner.py`` and should pass ``also_write_legacy=False`` to avoid
    double-rows. CLI callers should leave this True (default) so their runs
    appear in the UI.
    """
    if tenant_slug is None:
        tenant_slug = _default_tenant_slug()
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
        try:
            async with get_session() as session:
                run = Run(
                    tenant_slug=tenant_slug,
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
                    created_at=now,  # Explicit tz-naive; Run model default is tz-aware which collides with TIMESTAMP WITHOUT TIME ZONE column.
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
                _log.info(
                    "Persisted run %s for %s", outcome.run_id, envelope.protocol_key
                )
        except Exception as e:
            msg = f"Postgres persistence failed: {e}"
            _log.warning(msg)
            outcome.warnings.append(_warning("postgres_write_failed", msg))
            # Keep going — the legacy (UI) write still runs below so the user
            # sees their run in the portal even if the ce-db sink failed.

        # Dual-write to legacy ``run`` SQLModel table (UI source of truth).
        if also_write_legacy:
            legacy_warning = _write_legacy_run(
                envelope=envelope,
                tenant_slug=tenant_slug,
                trace_id=trace_id,
                total_cost=total_cost,
                error=error,
            )
            if legacy_warning:
                outcome.warnings.append(legacy_warning)

        return outcome
    finally:
        if implicit_tracker_used:
            try:
                from protocols.llm import set_cost_tracker

                set_cost_tracker(None)
            except Exception:
                _log.debug("Failed to clear implicit tracker", exc_info=True)
