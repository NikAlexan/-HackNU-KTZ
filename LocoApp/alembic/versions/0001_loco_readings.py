"""generated_readings table

Revision ID: 0001
Revises:
Create Date: 2026-04-04 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "generated_readings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("loco_id", sa.String(), nullable=False),
        sa.Column("loco_type", sa.String(10), nullable=False),
        sa.Column("ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("speed_kmh", sa.Float(), nullable=False),
        sa.Column("traction_mode", sa.String(10), nullable=False),
        sa.Column("health_index", sa.Float(), nullable=False),
        sa.Column("health_grade", sa.String(1), nullable=False),
        sa.Column("brake_pressure_atm", sa.Float(), nullable=False),
        sa.Column("error_code", sa.String(10), nullable=True),
        sa.Column("catenary_voltage_kv", sa.Float(), nullable=True),
        sa.Column("transformer_temp_c", sa.Float(), nullable=True),
        sa.Column("power_consumption_kw", sa.Float(), nullable=True),
        sa.Column("oil_temp_c", sa.Float(), nullable=True),
        sa.Column("fuel_level_liters", sa.Float(), nullable=True),
        sa.Column("engine_rpm", sa.Float(), nullable=True),
    )
    op.create_index("ix_gen_loco_ts", "generated_readings", ["loco_id", "ts"])


def downgrade() -> None:
    op.drop_index("ix_gen_loco_ts", table_name="generated_readings")
    op.drop_table("generated_readings")
