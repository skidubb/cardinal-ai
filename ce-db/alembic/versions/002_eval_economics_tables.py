"""Add eval economics tables and experiment key.

Revision ID: 002
Revises: 001
Create Date: 2026-03-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("eval_runs", sa.Column("experiment_key", sa.String(200), nullable=True))
    op.create_index("ix_eval_runs_experiment_key", "eval_runs", ["experiment_key"])

    op.create_table(
        "eval_samples",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("eval_run_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("question_id", sa.String(100), nullable=False),
        sa.Column("candidate_name", sa.String(200), nullable=False),
        sa.Column("replication_index", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("aggregate_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("score_variance", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_correct", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_baseline", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("total_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["eval_run_id"], ["eval_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_eval_samples_eval_run_id", "eval_samples", ["eval_run_id"])
    op.create_index("ix_eval_samples_question_id", "eval_samples", ["question_id"])
    op.create_index("ix_eval_samples_candidate_name", "eval_samples", ["candidate_name"])
    op.create_index("ix_eval_samples_created_at", "eval_samples", ["created_at"])

    op.create_table(
        "eval_regressions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("experiment_key", sa.String(200), nullable=False),
        sa.Column("question_id", sa.String(100), nullable=True),
        sa.Column("candidate_name", sa.String(200), nullable=False),
        sa.Column("baseline_candidate", sa.String(200), nullable=False),
        sa.Column("quality_delta", sa.Float(), nullable=False, server_default="0"),
        sa.Column("variance_delta", sa.Float(), nullable=False, server_default="0"),
        sa.Column("cost_per_correct_delta", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="neutral"),
        sa.Column("thresholds_json", postgresql.JSONB(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eval_regressions_experiment_key", "eval_regressions", ["experiment_key"])
    op.create_index("ix_eval_regressions_candidate_name", "eval_regressions", ["candidate_name"])
    op.create_index("ix_eval_regressions_created_at", "eval_regressions", ["created_at"])


def downgrade() -> None:
    op.drop_table("eval_regressions")
    op.drop_table("eval_samples")
    op.drop_index("ix_eval_runs_experiment_key", table_name="eval_runs")
    op.drop_column("eval_runs", "experiment_key")
