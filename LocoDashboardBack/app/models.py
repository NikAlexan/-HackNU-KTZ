import enum
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ---------------------------------------------------------------------------
# Python-side enums
# ---------------------------------------------------------------------------

class LocoType(str, enum.Enum):
    ELECTRIC = "ELECTRIC"
    DIESEL = "DIESEL"


class LocoStatus(str, enum.Enum):
    IN_MOTION = "IN_MOTION"
    STOPPED = "STOPPED"
    MAINTENANCE = "MAINTENANCE"


class TractionMode(str, enum.Enum):
    TRACTION = "TRACTION"
    BRAKE = "BRAKE"
    REGEN = "REGEN"
    IDLE = "IDLE"


class EventSeverity(str, enum.Enum):
    INFO = "INFO"
    WARN = "WARN"
    CRITICAL = "CRITICAL"


class HealthGrade(str, enum.Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


# ---------------------------------------------------------------------------
# SA-level enum types — create_type=False because Alembic owns CREATE TYPE
# ---------------------------------------------------------------------------

loco_type_enum = sa.Enum(LocoType, name="loco_type", create_type=False)
loco_status_enum = sa.Enum(LocoStatus, name="loco_status", create_type=False)
traction_mode_enum = sa.Enum(TractionMode, name="traction_mode", create_type=False)
severity_enum = sa.Enum(EventSeverity, name="event_severity", create_type=False)
health_grade_enum = sa.Enum(HealthGrade, name="health_grade", create_type=False)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Route(Base):
    __tablename__ = "routes"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    from_station: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    to_station: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    total_km: Mapped[float] = mapped_column(sa.Float, nullable=False)
    electrified: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    schedule_departure: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True))
    schedule_arrival: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True))

    waypoints: Mapped[list["RouteWaypoint"]] = relationship(
        "RouteWaypoint", back_populates="route", cascade="all, delete-orphan"
    )
    locomotives: Mapped[list["Locomotive"]] = relationship(
        "Locomotive", back_populates="route"
    )


class RouteWaypoint(Base):
    __tablename__ = "route_waypoints"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    route_id: Mapped[str] = mapped_column(sa.ForeignKey("routes.id"), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    km_mark: Mapped[float] = mapped_column(sa.Float, nullable=False)
    lat: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    speed_limit_kmh: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)

    route: Mapped["Route"] = relationship("Route", back_populates="waypoints")


class Locomotive(Base):
    __tablename__ = "locomotives"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    series: Mapped[str] = mapped_column(sa.String(60), nullable=False)
    number: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    type: Mapped[LocoType] = mapped_column(loco_type_enum, nullable=False)
    driver: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    status: Mapped[LocoStatus] = mapped_column(loco_status_enum, nullable=False)
    route_id: Mapped[str | None] = mapped_column(
        sa.ForeignKey("routes.id"), nullable=True
    )
    health_index: Mapped[float] = mapped_column(sa.Float, nullable=False)
    health_grade: Mapped[HealthGrade] = mapped_column(health_grade_enum, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
    )

    route: Mapped["Route | None"] = relationship("Route", back_populates="locomotives")
    telemetry: Mapped[list["TelemetryReading"]] = relationship(
        "TelemetryReading", back_populates="loco"
    )
    events: Mapped[list["Event"]] = relationship("Event", back_populates="loco")


class TelemetryReading(Base):
    __tablename__ = "telemetry_readings"
    __table_args__ = (
        sa.Index("ix_telemetry_loco_ts", "loco_id", "ts"),
    )

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    loco_id: Mapped[str] = mapped_column(sa.ForeignKey("locomotives.id"), nullable=False)
    ts: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=False)
    speed_kmh: Mapped[float] = mapped_column(sa.Float, nullable=False)
    brake_pressure_atm: Mapped[float] = mapped_column(sa.Float, nullable=False)
    battery_v: Mapped[float] = mapped_column(sa.Float, nullable=False)
    km_position: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    traction_mode: Mapped[TractionMode] = mapped_column(traction_mode_enum, nullable=False)
    error_code: Mapped[str | None] = mapped_column(sa.String(10), nullable=True)
    is_burst: Mapped[bool] = mapped_column(
        sa.Boolean, server_default="false", nullable=False
    )

    # ELECTRIC-specific (KZ8A) — nullable for diesel locos
    catenary_voltage_kv: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    pantograph_current_a: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    power_consumption_kw: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    regen_power_kw: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    power_factor: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    transformer_temp_c: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    # KZ8A has 8 traction motors
    td1_current_a: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    td2_current_a: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    td3_current_a: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    td4_current_a: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    td5_current_a: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    td6_current_a: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    td7_current_a: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    td8_current_a: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    td1_temp_c: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    td2_temp_c: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    td3_temp_c: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    td4_temp_c: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    td5_temp_c: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    td6_temp_c: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    td7_temp_c: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    td8_temp_c: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    pantograph_up: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True)
    regen_energy_kwh: Mapped[float | None] = mapped_column(sa.Float, nullable=True)

    # DIESEL-specific (ТЭ33А) — nullable for electric locos
    fuel_level_liters: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    fuel_consumption_lh: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    engine_rpm: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    oil_temp_c: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    coolant_temp_c: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    oil_pressure_bar: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    traction_force_kn: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    main_gen_voltage_v: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    axle1_load_t: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    axle2_load_t: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    axle3_load_t: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    axle4_load_t: Mapped[float | None] = mapped_column(sa.Float, nullable=True)

    loco: Mapped["Locomotive"] = relationship("Locomotive", back_populates="telemetry")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    loco_id: Mapped[str] = mapped_column(sa.ForeignKey("locomotives.id"), nullable=False)
    ts: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=False)
    severity: Mapped[EventSeverity] = mapped_column(severity_enum, nullable=False)
    category: Mapped[str] = mapped_column(sa.String(30), nullable=False)
    title: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    parameter_key: Mapped[str] = mapped_column(sa.String(60), nullable=False)
    parameter_value: Mapped[float] = mapped_column(sa.Float, nullable=False)
    threshold: Mapped[float] = mapped_column(sa.Float, nullable=False)
    auto_generated: Mapped[bool] = mapped_column(
        sa.Boolean, server_default="true", nullable=False
    )
    acknowledged: Mapped[bool] = mapped_column(
        sa.Boolean, server_default="false", nullable=False
    )
    recommended_action: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    loco: Mapped["Locomotive"] = relationship("Locomotive", back_populates="events")


class TelemetryAggregate(Base):
    """5-minute aggregate received from loco-app reporter."""

    __tablename__ = "telemetry_aggregates"
    __table_args__ = (sa.Index("ix_agg_loco_period", "loco_id", "period_start"),)

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    loco_id: Mapped[str] = mapped_column(sa.String, nullable=False)
    loco_type: Mapped[str] = mapped_column(sa.String(10), nullable=False)
    period_start: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=False)
    readings_count: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    avg_speed_kmh: Mapped[float] = mapped_column(sa.Float, nullable=False)
    max_temp_c: Mapped[float] = mapped_column(sa.Float, nullable=False)
    min_voltage_kv: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    avg_health_index: Mapped[float] = mapped_column(sa.Float, nullable=False)
    final_health_grade: Mapped[str] = mapped_column(sa.String(1), nullable=False)
    error_count: Mapped[int] = mapped_column(sa.Integer, nullable=False)
