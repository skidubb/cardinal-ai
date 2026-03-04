"""Pipeline endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from api.database import get_session
from api.models import Pipeline, PipelineStep

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


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
