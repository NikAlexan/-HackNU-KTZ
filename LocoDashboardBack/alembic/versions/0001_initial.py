"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-04 00:00:00.000000
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

ENUM_TYPES = [
    ("loco_type",      ["ELECTRIC", "DIESEL"]),
    ("loco_status",    ["IN_MOTION", "STOPPED", "MAINTENANCE"]),
    ("traction_mode",  ["TRACTION", "BRAKE", "REGEN", "IDLE"]),
    ("event_severity", ["INFO", "WARN", "CRITICAL"]),
    ("health_grade",   ["A", "B", "C", "D", "E"]),
]


def upgrade() -> None:
    # 1. Create PostgreSQL native enum types
    for enum_name, values in ENUM_TYPES:
        op.execute(
            f"CREATE TYPE {enum_name} AS ENUM "
            f"({', '.join(repr(v) for v in values)})"
        )

    # Helper: PG_ENUM ref without auto-create
    def _enum(name: str) -> PG_ENUM:
        return PG_ENUM(name=name, create_type=False)

    # 2. routes
    op.create_table(
        "routes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("from_station", sa.String(120), nullable=False),
        sa.Column("to_station", sa.String(120), nullable=False),
        sa.Column("total_km", sa.Float(), nullable=False),
        sa.Column("electrified", sa.Boolean(), nullable=False),
        sa.Column("schedule_departure", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("schedule_arrival", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    # 3. route_waypoints
    op.create_table(
        "route_waypoints",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("route_id", sa.String(), sa.ForeignKey("routes.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("km_mark", sa.Float(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("speed_limit_kmh", sa.Integer(), nullable=True),
    )

    # 4. locomotives
    op.create_table(
        "locomotives",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("series", sa.String(60), nullable=False),
        sa.Column("number", sa.String(20), nullable=False),
        sa.Column("type", _enum("loco_type"), nullable=False),
        sa.Column("driver", sa.String(120), nullable=False),
        sa.Column("status", _enum("loco_status"), nullable=False),
        sa.Column("route_id", sa.String(), sa.ForeignKey("routes.id"), nullable=True),
        sa.Column("health_index", sa.Float(), nullable=False),
        sa.Column("health_grade", _enum("health_grade"), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # 5. telemetry_readings
    op.create_table(
        "telemetry_readings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("loco_id", sa.String(), sa.ForeignKey("locomotives.id"), nullable=False),
        sa.Column("ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("speed_kmh", sa.Float(), nullable=False),
        sa.Column("brake_pressure_atm", sa.Float(), nullable=False),
        sa.Column("battery_v", sa.Float(), nullable=False),
        sa.Column("km_position", sa.Integer(), nullable=False),
        sa.Column("traction_mode", _enum("traction_mode"), nullable=False),
        sa.Column("error_code", sa.String(10), nullable=True),
        sa.Column("is_burst", sa.Boolean(), server_default="false", nullable=False),
        # ELECTRIC / KZ8A fields
        sa.Column("catenary_voltage_kv", sa.Float(), nullable=True),
        sa.Column("pantograph_current_a", sa.Float(), nullable=True),
        sa.Column("power_consumption_kw", sa.Float(), nullable=True),
        sa.Column("regen_power_kw", sa.Float(), nullable=True),
        sa.Column("power_factor", sa.Float(), nullable=True),
        sa.Column("transformer_temp_c", sa.Float(), nullable=True),
        sa.Column("td1_current_a", sa.Float(), nullable=True),
        sa.Column("td2_current_a", sa.Float(), nullable=True),
        sa.Column("td3_current_a", sa.Float(), nullable=True),
        sa.Column("td4_current_a", sa.Float(), nullable=True),
        sa.Column("td5_current_a", sa.Float(), nullable=True),
        sa.Column("td6_current_a", sa.Float(), nullable=True),
        sa.Column("td7_current_a", sa.Float(), nullable=True),
        sa.Column("td8_current_a", sa.Float(), nullable=True),
        sa.Column("td1_temp_c", sa.Float(), nullable=True),
        sa.Column("td2_temp_c", sa.Float(), nullable=True),
        sa.Column("td3_temp_c", sa.Float(), nullable=True),
        sa.Column("td4_temp_c", sa.Float(), nullable=True),
        sa.Column("td5_temp_c", sa.Float(), nullable=True),
        sa.Column("td6_temp_c", sa.Float(), nullable=True),
        sa.Column("td7_temp_c", sa.Float(), nullable=True),
        sa.Column("td8_temp_c", sa.Float(), nullable=True),
        sa.Column("pantograph_up", sa.Boolean(), nullable=True),
        sa.Column("regen_energy_kwh", sa.Float(), nullable=True),
        # DIESEL / ТЭ33А fields
        sa.Column("fuel_level_liters", sa.Float(), nullable=True),
        sa.Column("fuel_consumption_lh", sa.Float(), nullable=True),
        sa.Column("engine_rpm", sa.Float(), nullable=True),
        sa.Column("oil_temp_c", sa.Float(), nullable=True),
        sa.Column("coolant_temp_c", sa.Float(), nullable=True),
        sa.Column("oil_pressure_bar", sa.Float(), nullable=True),
        sa.Column("traction_force_kn", sa.Float(), nullable=True),
        sa.Column("main_gen_voltage_v", sa.Float(), nullable=True),
        sa.Column("axle1_load_t", sa.Float(), nullable=True),
        sa.Column("axle2_load_t", sa.Float(), nullable=True),
        sa.Column("axle3_load_t", sa.Float(), nullable=True),
        sa.Column("axle4_load_t", sa.Float(), nullable=True),
    )

    # Composite index — critical for API performance
    op.create_index("ix_telemetry_loco_ts", "telemetry_readings", ["loco_id", "ts"])

    # 6. events
    op.create_table(
        "events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("loco_id", sa.String(), sa.ForeignKey("locomotives.id"), nullable=False),
        sa.Column("ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("severity", _enum("event_severity"), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("parameter_key", sa.String(60), nullable=False),
        sa.Column("parameter_value", sa.Float(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("auto_generated", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("acknowledged", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("events")
    op.drop_index("ix_telemetry_loco_ts", table_name="telemetry_readings")
    op.drop_table("telemetry_readings")
    op.drop_table("locomotives")
    op.drop_table("route_waypoints")
    op.drop_table("routes")
    for enum_name, _ in reversed(ENUM_TYPES):
        op.execute(f"DROP TYPE {enum_name}")
