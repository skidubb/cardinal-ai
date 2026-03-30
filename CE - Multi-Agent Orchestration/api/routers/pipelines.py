"""Pipeline endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from api.database import engine, get_session
from api.models import Pipeline, PipelineStep, Run
from api.pipeline_presets import PIPELINE_PRESETS
from api.routers.runs import PipelineRunRequest
from api.runner import _active_run_tasks, run_pipeline_stream

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


# ── POST /run — start a pipeline run with SSE streaming ──────────────────────

async def _watch_disconnect(request: Request, run_id: int) -> None:
    """Poll for client disconnect and cancel the active orchestrator task when detected."""
    while not await request.is_disconnected():
        await asyncio.sleep(0.5)
    task = _active_run_tasks.get(run_id)
    if task and not task.done():
        task.cancel()


@router.post("/run")
async def start_pipeline_run(payload: PipelineRunRequest, request: Request) -> EventSourceResponse:
    """Start a pipeline run and stream SSE events."""
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

    async def _guarded_stream():
        disconnect_watcher = asyncio.create_task(_watch_disconnect(request, run_id))
        try:
            async for chunk in run_pipeline_stream(
                run_id=run_id,
                steps=steps,
                question=payload.question,
                agent_keys=payload.agent_keys,
            ):
                yield chunk
        finally:
            disconnect_watcher.cancel()

    return StreamingResponse(
        _guarded_stream(),
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
