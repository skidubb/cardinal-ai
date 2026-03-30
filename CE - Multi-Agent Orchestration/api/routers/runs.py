"""Run endpoints — list/get runs and stream replay.

POST /run endpoints have moved to:
  POST /api/protocols/run  (api/routers/protocols.py)
  POST /api/pipelines/run  (api/routers/pipelines.py)
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, col, select
from sse_starlette.sse import EventSourceResponse

from api.database import engine, get_session
from api.models import AgentOutput, Run, RunStep
from api.report_helpers import build_envelope_from_db
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from protocols.protocol_report import from_envelope as _report_from_envelope

router = APIRouter(prefix="/api/runs", tags=["runs"])


def _parse_telemetry_warnings(error_message: str | None) -> list[dict]:
    if not error_message:
        return []
    try:
        payload = json.loads(error_message)
    except Exception:
        return []
    if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        return payload
    return []


# ── Request schemas ──────────────────────────────────────────────────────────

class ProtocolRunRequest(BaseModel):
    protocol_key: str
    question: str
    agent_keys: list[str]
    thinking_model: str = THINKING_MODEL
    orchestration_model: str = ORCHESTRATION_MODEL
    rounds: int | None = None
    no_tools: bool = False


class PipelineStepRequest(BaseModel):
    protocol_key: str
    question_template: str
    thinking_model: str = THINKING_MODEL
    orchestration_model: str = ORCHESTRATION_MODEL
    rounds: int | None = None
    output_passthrough: bool = True
    no_tools: bool = False


class PipelineRunRequest(BaseModel):
    pipeline_name: str = ""
    question: str
    agent_keys: list[str]
    steps: list[PipelineStepRequest]


# ── List / Get ───────────────────────────────────────────────────────────────

@router.get("")
def list_runs(
    limit: int = 20,
    offset: int = 0,
    session: Session = Depends(get_session),
) -> list[dict]:
    runs = list(
        session.exec(
            select(Run).order_by(col(Run.started_at).desc()).offset(offset).limit(limit)
        ).all()
    )
    return [
        {
            "id": r.id,
            "type": r.type,
            "protocol_key": r.protocol_key,
            "pipeline_id": r.pipeline_id,
            "question": r.question,
            "team_id": r.team_id,
            "status": r.status,
            "cost_usd": r.cost_usd,
            "trace_id": r.trace_id,
            "error_message": r.error_message,
            "telemetry_warnings": _parse_telemetry_warnings(r.error_message),
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in runs
    ]


# ── GET /{run_id}/stream — MUST be declared before GET /{run_id} ──────────────

async def _replay_completed_run(run: Run, session: Session) -> AsyncGenerator[str, None]:
    """Yield SSE events replaying a completed run's stored outputs."""

    def _sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    yield _sse("run_start", {"run_id": run.id, "protocol_key": run.protocol_key, "replay": True})

    agent_outputs = session.exec(
        select(AgentOutput).where(AgentOutput.run_id == run.id)
    ).all()

    for out in agent_outputs:
        if out.agent_key == "_synthesis":
            yield _sse("synthesis", {"text": out.output_text, "replay": True})
        else:
            payload = {
                "agent_key": out.agent_key,
                "model": out.model,
                "output_text": out.output_text,
                "input_tokens": out.input_tokens,
                "output_tokens": out.output_tokens,
                "cost_usd": out.cost_usd,
                "replay": True,
            }
            yield _sse("agent_output", payload)

    yield _sse(
        "run_complete",
        {
            "run_id": run.id,
            "status": run.status,
            "cost_usd": run.cost_usd,
            "trace_id": run.trace_id,
            "replay": True,
        },
    )


@router.get("/{run_id}/stream")
async def stream_run(run_id: int, session: Session = Depends(get_session)) -> EventSourceResponse:
    """Replay a completed run as SSE events."""
    run = session.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status not in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=202, detail="Run still in progress")
    return EventSourceResponse(
        _replay_completed_run(run, session),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no"},
    )


@router.get("/{run_id}")
def get_run(run_id: int, session: Session = Depends(get_session)) -> dict:
    run = session.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    steps = session.exec(
        select(RunStep).where(RunStep.run_id == run_id).order_by(RunStep.step_order)
    ).all()
    outputs = session.exec(
        select(AgentOutput).where(AgentOutput.run_id == run_id)
    ).all()

    response: dict = {
        "id": run.id,
        "type": run.type,
        "protocol_key": run.protocol_key,
        "pipeline_id": run.pipeline_id,
        "question": run.question,
        "team_id": run.team_id,
        "status": run.status,
        "cost_usd": run.cost_usd,
        "trace_id": run.trace_id,
        "error_message": run.error_message,
        "telemetry_warnings": _parse_telemetry_warnings(run.error_message),
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "steps": [
            {
                "id": s.id,
                "step_order": s.step_order,
                "protocol_key": s.protocol_key,
                "status": s.status,
                "cost_usd": s.cost_usd,
            }
            for s in steps
        ],
        "outputs": [
            {
                "id": o.id,
                "agent_key": o.agent_key,
                "model": o.model,
                "output_text": o.output_text,
                "tool_calls": json.loads(o.tool_calls_json) if o.tool_calls_json != "[]" else [],
                "input_tokens": o.input_tokens,
                "output_tokens": o.output_tokens,
                "cost_usd": o.cost_usd,
            }
            for o in outputs
        ],
    }

    # Attach structured protocol_report when run is completed
    if run.status == "completed":
        try:
            envelope = build_envelope_from_db(run, session)
            verdict: dict | None = None
            raw_verdict = getattr(run, "judge_verdict_json", "{}")
            if raw_verdict and raw_verdict != "{}":
                try:
                    verdict = json.loads(raw_verdict)
                except (json.JSONDecodeError, ValueError):
                    verdict = None
            report = _report_from_envelope(envelope, verdict)
            response["protocol_report"] = report.as_dict()
        except Exception:
            response["protocol_report"] = None

    return response
