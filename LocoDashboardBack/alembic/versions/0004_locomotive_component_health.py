"""Add component_health JSON column to locomotives

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-05
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "locomotives",
        sa.Column("component_health", sa.JSON, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("locomotives", "component_health")
