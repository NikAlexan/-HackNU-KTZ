"""add telemetry_aggregates table

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-04 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telemetry_aggregates",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("loco_id", sa.String(), nullable=False),
        sa.Column("loco_type", sa.String(10), nullable=False),
        sa.Column("period_start", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("period_end", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("readings_count", sa.Integer(), nullable=False),
        sa.Column("avg_speed_kmh", sa.Float(), nullable=False),
        sa.Column("max_temp_c", sa.Float(), nullable=False),
        sa.Column("min_voltage_kv", sa.Float(), nullable=True),
        sa.Column("avg_health_index", sa.Float(), nullable=False),
        sa.Column("final_health_grade", sa.String(1), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
    )
    op.create_index("ix_agg_loco_period", "telemetry_aggregates", ["loco_id", "period_start"])


def downgrade() -> None:
    op.drop_index("ix_agg_loco_period", table_name="telemetry_aggregates")
    op.drop_table("telemetry_aggregates")
