"""component_health table

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-05
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "component_health",
        sa.Column("loco_id", sa.String(64), primary_key=True, nullable=False),
        sa.Column("component", sa.String(64), primary_key=True, nullable=False),
        sa.Column(
            "health",
            sa.Float,
            nullable=False,
            server_default=sa.text("100.0"),
        ),
        sa.Column(
            "risk_accum",
            sa.Float,
            nullable=False,
            server_default=sa.text("0.0"),
        ),
        sa.Column("last_repair", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("component_health")
