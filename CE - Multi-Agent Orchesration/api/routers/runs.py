"""Run endpoints — start protocol/pipeline runs with SSE streaming."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, col, select
from sse_starlette.sse import EventSourceResponse

from api.database import engine, get_session
from api.models import AgentOutput, Run, RunStep
from api.runner import run_pipeline_stream, run_protocol_stream
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL

router = APIRouter(prefix="/api/runs", tags=["runs"])


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
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in runs
    ]


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

    return {
        "id": run.id,
        "type": run.type,
        "protocol_key": run.protocol_key,
        "pipeline_id": run.pipeline_id,
        "question": run.question,
        "team_id": run.team_id,
        "status": run.status,
        "cost_usd": run.cost_usd,
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


# ── Start protocol run (SSE) ────────────────────────────────────────────────

@router.post("/protocol")
async def start_protocol_run(payload: ProtocolRunRequest) -> EventSourceResponse:
    # Create run record
    with Session(engine) as session:
        run = Run(
            type="protocol",
            protocol_key=payload.protocol_key,
            question=payload.question,
            status="pending",
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    return EventSourceResponse(
        run_protocol_stream(
            run_id=run_id,
            protocol_key=payload.protocol_key,
            question=payload.question,
            agent_keys=payload.agent_keys,
            thinking_model=payload.thinking_model,
            orchestration_model=payload.orchestration_model,
            rounds=payload.rounds,
            no_tools=payload.no_tools,
        ),
        media_type="text/event-stream",
    )


# ── Start pipeline run (SSE) ────────────────────────────────────────────────

@router.post("/pipeline")
async def start_pipeline_run(payload: PipelineRunRequest) -> EventSourceResponse:
    with Session(engine) as session:
        run = Run(
            type="pipeline",
            question=payload.question,
            status="pending",
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    steps = [
        {
            "protocol_key": s.protocol_key,
            "question_template": s.question_template,
            "thinking_model": s.thinking_model,
            "orchestration_model": s.orchestration_model,
            "rounds": s.rounds,
            "output_passthrough": s.output_passthrough,
            "no_tools": s.no_tools,
        }
        for s in payload.steps
    ]

    return EventSourceResponse(
        run_pipeline_stream(
            run_id=run_id,
            steps=steps,
            question=payload.question,
            agent_keys=payload.agent_keys,
        ),
        media_type="text/event-stream",
    )
