"""Initial schema.

Revision ID: 001
Revises: None
Create Date: 2026-03-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agents table
    op.create_table(
        "agents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column("tools_json", postgresql.JSONB(), nullable=True),
        sa.Column("mcp_servers_json", postgresql.JSONB(), nullable=True),
        sa.Column("kb_namespaces_json", postgresql.JSONB(), nullable=True),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index("ix_agents_key", "agents", ["key"])
    op.create_index("ix_agents_category", "agents", ["category"])

    # Runs table
    op.create_table(
        "runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("protocol_key", sa.String(100), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("agent_keys", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("source", sa.String(20), nullable=False, server_default="cli"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("result_json", postgresql.JSONB(), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("total_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("langfuse_trace_id", sa.String(200), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_runs_protocol_key", "runs", ["protocol_key"])
    op.create_index("ix_runs_status", "runs", ["status"])
    op.create_index("ix_runs_created_at", "runs", ["created_at"])

    # Agent outputs table
    op.create_table(
        "agent_outputs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("agent_key", sa.String(100), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_agent_outputs_run_id", "agent_outputs", ["run_id"])
    op.create_index("ix_agent_outputs_agent_key", "agent_outputs", ["agent_key"])

    # Eval runs table
    op.create_table(
        "eval_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("rubric_name", sa.String(200), nullable=False),
        sa.Column("judge_backend", sa.String(100), nullable=False),
        sa.Column("aggregate_score", sa.Float(), nullable=False),
        sa.Column("scores_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("question_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_eval_runs_run_id", "eval_runs", ["run_id"])


def downgrade() -> None:
    op.drop_table("eval_runs")
    op.drop_table("agent_outputs")
    op.drop_table("runs")
    op.drop_table("agents")
