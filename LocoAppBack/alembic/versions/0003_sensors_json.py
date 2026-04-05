"""Add sensors_json, drop old type-specific columns from generated_readings

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-05 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add sensors_json column
    op.add_column(
        "generated_readings",
        sa.Column("sensors_json", sa.JSON(), nullable=True),
    )
    # Fill existing rows with empty JSON (there shouldn't be any in dev, but just in case)
    op.execute("UPDATE generated_readings SET sensors_json = '{}' WHERE sensors_json IS NULL")
    # Make it not nullable
    op.alter_column("generated_readings", "sensors_json", nullable=False)

    # Drop old type-specific columns
    for col in (
        "brake_pressure_atm",
        "catenary_voltage_kv",
        "transformer_temp_c",
        "power_consumption_kw",
        "oil_temp_c",
        "fuel_level_liters",
        "engine_rpm",
    ):
        try:
            op.drop_column("generated_readings", col)
        except Exception:
            pass  # column may not exist if DB was freshly created with new model


def downgrade() -> None:
    op.drop_column("generated_readings", "sensors_json")
    op.add_column("generated_readings", sa.Column("brake_pressure_atm", sa.Float(), nullable=True))
    op.add_column("generated_readings", sa.Column("catenary_voltage_kv", sa.Float(), nullable=True))
    op.add_column("generated_readings", sa.Column("transformer_temp_c", sa.Float(), nullable=True))
    op.add_column("generated_readings", sa.Column("power_consumption_kw", sa.Float(), nullable=True))
    op.add_column("generated_readings", sa.Column("oil_temp_c", sa.Float(), nullable=True))
    op.add_column("generated_readings", sa.Column("fuel_level_liters", sa.Float(), nullable=True))
    op.add_column("generated_readings", sa.Column("engine_rpm", sa.Float(), nullable=True))
