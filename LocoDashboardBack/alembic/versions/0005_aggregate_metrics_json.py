"""Add metrics_json to telemetry_aggregates

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-05 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "telemetry_aggregates",
        sa.Column("metrics_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("telemetry_aggregates", "metrics_json")
