"""Add tenant_slug to runs (multi-tenancy).

Backfills all existing rows to 'cardinal-element' (CE's own reference tenant).
Backward-compatible: existing CLI workflows continue to work via the default.

Revision ID: 004
Revises: 003
"""

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"


def upgrade() -> None:
    # Add column with server_default so existing rows get backfilled atomically.
    op.add_column(
        "runs",
        sa.Column(
            "tenant_slug",
            sa.String(100),
            nullable=False,
            server_default="cardinal-element",
        ),
    )
    op.create_index("ix_runs_tenant_slug", "runs", ["tenant_slug"])


def downgrade() -> None:
    op.drop_index("ix_runs_tenant_slug", table_name="runs")
    op.drop_column("runs", "tenant_slug")
