"""Team endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from api.database import get_session
from api.models import Team

router = APIRouter(prefix="/api/teams", tags=["teams"])


class TeamCreate(BaseModel):
    name: str
    description: str = ""
    agent_keys: list[str] = []


class TeamResponse(BaseModel):
    id: int
    name: str
    description: str
    agent_keys: list[str]
    created_at: str
    last_used_at: str | None


def _team_to_response(team: Team) -> TeamResponse:
    return TeamResponse(
        id=team.id,  # type: ignore[arg-type]
        name=team.name,
        description=team.description,
        agent_keys=json.loads(team.agent_keys_json),
        created_at=team.created_at.isoformat(),
        last_used_at=team.last_used_at.isoformat() if team.last_used_at else None,
    )


@router.get("")
def list_teams(session: Session = Depends(get_session)) -> list[TeamResponse]:
    teams = session.exec(select(Team)).all()
    return [_team_to_response(t) for t in teams]


@router.post("", status_code=201)
def create_team(payload: TeamCreate, session: Session = Depends(get_session)) -> TeamResponse:
    team = Team(
        name=payload.name,
        description=payload.description,
        agent_keys_json=json.dumps(payload.agent_keys),
    )
    session.add(team)
    session.commit()
    session.refresh(team)
    return _team_to_response(team)


@router.get("/{team_id}")
def get_team(team_id: int, session: Session = Depends(get_session)) -> TeamResponse:
    team = session.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return _team_to_response(team)


@router.put("/{team_id}")
def update_team(team_id: int, payload: TeamCreate, session: Session = Depends(get_session)) -> TeamResponse:
    team = session.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    team.name = payload.name
    team.description = payload.description
    team.agent_keys_json = json.dumps(payload.agent_keys)
    session.add(team)
    session.commit()
    session.refresh(team)
    return _team_to_response(team)


@router.delete("/{team_id}", status_code=204)
def delete_team(team_id: int, session: Session = Depends(get_session)) -> None:
    team = session.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    session.delete(team)
    session.commit()
