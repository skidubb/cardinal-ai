"""Pipeline endpoints."""

from __future__ import annotations

import asyncio
import json as _json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlmodel import Session, col, select

from api.database import engine, get_session
from api.models import Pipeline, PipelineStep, Run, RunStep
from api.pipeline_presets import PIPELINE_PRESETS
from api.routers.runs import PipelineRunRequest
from api.runner import run_pipeline_stream

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


# ── POST /run — start a pipeline run with SSE streaming ──────────────────────

@router.post("/run")
async def start_pipeline_run(payload: PipelineRunRequest, request: Request) -> StreamingResponse:
    """Start a pipeline run and stream SSE events.

    Runs complete server-side regardless of client disconnect. Close the
    browser tab and the run keeps going — check Run History for results.
    """
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

    with Session(engine) as session:
        run = Run(
            type="pipeline",
            question=payload.question,
            status="pending",
            agent_keys_json=_json.dumps(payload.agent_keys),
            steps_json=_json.dumps(steps),
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    # Run pipeline as a background task so it survives client disconnect.
    # SSE generator drains the queue; if client drops, task keeps going.
    event_queue: asyncio.Queue = asyncio.Queue(maxsize=5000)

    async def _run_pipeline():
        try:
            async for chunk in run_pipeline_stream(
                run_id=run_id,
                steps=steps,
                question=payload.question,
                agent_keys=payload.agent_keys,
            ):
                await event_queue.put(chunk)
        finally:
            await event_queue.put(None)  # sentinel

    asyncio.create_task(_run_pipeline())

    async def _stream():
        while True:
            chunk = await event_queue.get()
            if chunk is None:
                break
            yield chunk

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── POST /resume/{run_id} — resume a failed/cancelled pipeline ──────────────

@router.post("/resume/{run_id}")
async def resume_pipeline_run(run_id: int, request: Request) -> StreamingResponse:
    """Resume a failed or cancelled pipeline from the last completed step."""
    with Session(engine) as session:
        run = session.get(Run, run_id)
        if not run or run.type != "pipeline":
            raise HTTPException(status_code=404, detail="Pipeline run not found")
        if run.status not in ("failed", "cancelled"):
            raise HTTPException(status_code=400, detail=f"Run is {run.status}, not resumable")

        # Load original config
        steps = _json.loads(run.steps_json) if run.steps_json and run.steps_json != "[]" else []
        agent_keys = _json.loads(run.agent_keys_json) if run.agent_keys_json and run.agent_keys_json != "[]" else []
        if not steps or not agent_keys:
            raise HTTPException(status_code=400, detail="Run missing step/agent config — cannot resume")

        # Find last completed step
        completed_steps = list(session.exec(
            select(RunStep)
            .where(RunStep.run_id == run_id, RunStep.status == "completed")
            .order_by(col(RunStep.step_order).desc())
        ).all())

        start_from = 0
        prev_output = ""
        if completed_steps:
            last = completed_steps[0]
            start_from = last.step_order + 1
            prev_output = last.output_text or ""

        if start_from >= len(steps):
            raise HTTPException(status_code=400, detail="All steps already completed")

        # Reset run status
        run.status = "running"
        run.error_message = None
        session.add(run)
        session.commit()

    async def _stream():
        async for chunk in run_pipeline_stream(
            run_id=run_id,
            steps=steps,
            question=run.question,
            agent_keys=agent_keys,
            start_from_step=start_from,
            initial_prev_output=prev_output,
        ):
            yield chunk

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("")
def list_pipelines(session: Session = Depends(get_session)) -> list[dict]:
    db_pipelines = [_pipeline_with_steps(p, session) for p in session.exec(select(Pipeline)).all()]
    return PIPELINE_PRESETS + db_pipelines  # noqa: RUF005


@router.post("", status_code=201)
def create_pipeline(
    payload: dict,
    session: Session = Depends(get_session),
) -> dict:
    steps_data = payload.pop("steps", [])
    pipeline = Pipeline(**payload)
    session.add(pipeline)
    session.commit()
    session.refresh(pipeline)

    for i, step_data in enumerate(steps_data):
        step = PipelineStep(pipeline_id=pipeline.id, order=i, **step_data)
        session.add(step)
    session.commit()
    session.refresh(pipeline)

    return _pipeline_with_steps(pipeline, session)


@router.delete("/{pipeline_id}", status_code=204)
def delete_pipeline(pipeline_id: int, session: Session = Depends(get_session)):
    pipeline = session.get(Pipeline, pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    steps = session.exec(
        select(PipelineStep).where(PipelineStep.pipeline_id == pipeline_id)
    ).all()
    for step in steps:
        session.delete(step)
    session.delete(pipeline)
    session.commit()


@router.get("/{pipeline_id}")
def get_pipeline(pipeline_id: int, session: Session = Depends(get_session)) -> dict:
    pipeline = session.get(Pipeline, pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return _pipeline_with_steps(pipeline, session)


def _pipeline_with_steps(pipeline: Pipeline, session: Session) -> dict:
    steps = session.exec(
        select(PipelineStep)
        .where(PipelineStep.pipeline_id == pipeline.id)
        .order_by(PipelineStep.order)
    ).all()
    return {
        "id": pipeline.id,
        "name": pipeline.name,
        "description": pipeline.description,
        "team_id": pipeline.team_id,
        "created_at": pipeline.created_at.isoformat(),
        "steps": [
            {
                "id": s.id,
                "order": s.order,
                "protocol_key": s.protocol_key,
                "question_template": s.question_template,
                "agent_key_override_json": s.agent_key_override_json,
                "rounds": s.rounds,
                "thinking_model": s.thinking_model,
                "orchestration_model": s.orchestration_model,
                "output_passthrough": s.output_passthrough,
                "no_tools": s.no_tools,
            }
            for s in steps
        ],
    }
