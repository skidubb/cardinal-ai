"""Add protocol_insights and run_learnings tables.

Revision ID: 003
Revises: 002
"""

revision = "003"
down_revision = "002"

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


def upgrade() -> None:
    op.create_table(
        "protocol_insights",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("protocol_key", sa.String(100), nullable=False),
        sa.Column("question_category", sa.String(50), nullable=False),
        sa.Column("insight_type", sa.String(50), nullable=False),
        sa.Column("insight_json", JSONB, server_default="{}"),
        sa.Column("confidence", sa.Float(), server_default="0.0"),
        sa.Column("sample_size", sa.Integer(), server_default="0"),
        sa.Column("best_synthesis", sa.Text(), nullable=True),
        sa.Column("best_score", sa.Float(), nullable=True),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "protocol_key", "question_category", "insight_type",
            name="uq_insights_lookup",
        ),
    )
    op.create_index(
        "ix_insights_lookup",
        "protocol_insights",
        ["protocol_key", "question_category", "insight_type"],
    )

    op.create_table(
        "run_learnings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("run_id", sa.String(100), nullable=False),
        sa.Column("protocol_key", sa.String(100), nullable=False),
        sa.Column("question_categories", JSONB, server_default="[]"),
        sa.Column("eval_score", sa.Float(), nullable=True),
        sa.Column("config_json", JSONB, server_default="{}"),
        sa.Column("cost_usd", sa.Float(), server_default="0.0"),
        sa.Column("synthesis_excerpt", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_run_learnings_protocol", "run_learnings", ["protocol_key"])
    op.create_index("ix_run_learnings_score", "run_learnings", ["eval_score"])
    op.create_index(
        "ix_run_learnings_categories", "run_learnings",
        ["question_categories"], postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_table("run_learnings")
    op.drop_table("protocol_insights")
