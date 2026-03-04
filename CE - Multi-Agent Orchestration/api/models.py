"""SQLModel models for the orchestrator API."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Agents ────────────────────────────────────────────────────────────────────

class Agent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)
    name: str
    category: str = ""
    model: str = ""
    temperature: float = 1.0
    system_prompt: str = ""
    max_tokens: int = 8192
    tools_json: str = "[]"
    mcp_servers_json: str = "[]"
    kb_namespaces_json: str = "[]"
    kb_write_enabled: bool = False
    deliverable_template: str = ""
    frameworks_json: str = "[]"
    delegation_json: str = "[]"
    personality: str = ""
    communication_style: str = ""
    constraints_json: str = "[]"
    is_builtin: bool = False
    created_at: datetime = Field(default_factory=_now)


# ── Teams ─────────────────────────────────────────────────────────────────────

class Team(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str = ""
    agent_keys_json: str = "[]"
    created_at: datetime = Field(default_factory=_now)
    last_used_at: Optional[datetime] = None


# ── Pipelines ─────────────────────────────────────────────────────────────────

class Pipeline(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str = ""
    team_id: Optional[int] = Field(default=None, foreign_key="team.id")
    created_at: datetime = Field(default_factory=_now)


class PipelineStep(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    pipeline_id: int = Field(foreign_key="pipeline.id")
    order: int = 0
    protocol_key: str = ""
    question_template: str = ""
    agent_key_override_json: str = "[]"
    rounds: Optional[int] = None
    thinking_model: str = ""
    orchestration_model: str = ""
    output_passthrough: bool = False
    no_tools: bool = False


# ── Runs ──────────────────────────────────────────────────────────────────────

class Run(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: str = ""
    protocol_key: str = ""
    pipeline_id: Optional[int] = None
    question: str = ""
    team_id: Optional[int] = None
    status: str = "pending"
    cost_usd: float = 0.0
    started_at: datetime = Field(default_factory=_now)
    completed_at: Optional[datetime] = None


class RunStep(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="run.id")
    step_order: int = 0
    protocol_key: str = ""
    status: str = "pending"
    cost_usd: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class AgentOutput(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="run.id")
    run_step_id: Optional[int] = Field(default=None, foreign_key="runstep.id")
    agent_key: str = ""
    model: str = ""
    output_text: str = ""
    tool_calls_json: str = "[]"
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
