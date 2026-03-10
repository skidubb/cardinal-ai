"""Pipeline endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select
from sse_starlette.sse import EventSourceResponse

from api.database import engine, get_session
from api.models import Pipeline, PipelineStep, Run
from api.routers.runs import PipelineRunRequest
from api.runner import run_pipeline_stream

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


# ── POST /run — start a pipeline run with SSE streaming ──────────────────────

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

    return EventSourceResponse(
        run_pipeline_stream(
            run_id=run_id,
            steps=steps,
            question=payload.question,
            agent_keys=payload.agent_keys,
        ),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no"},
    )


@router.get("")
def list_pipelines(session: Session = Depends(get_session)) -> list[Pipeline]:
    return list(session.exec(select(Pipeline)).all())


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
            }
            for s in steps
        ],
    }
