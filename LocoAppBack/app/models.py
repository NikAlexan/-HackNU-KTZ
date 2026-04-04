from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GeneratedReading(Base):
    """In-memory generated telemetry reading stored for aggregation."""

    __tablename__ = "generated_readings"
    __table_args__ = (sa.Index("ix_gen_loco_ts", "loco_id", "ts"),)

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    loco_id: Mapped[str] = mapped_column(sa.String, nullable=False)
    loco_type: Mapped[str] = mapped_column(sa.String(10), nullable=False)
    ts: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=False)
    speed_kmh: Mapped[float] = mapped_column(sa.Float, nullable=False)
    traction_mode: Mapped[str] = mapped_column(sa.String(10), nullable=False)
    health_index: Mapped[float] = mapped_column(sa.Float, nullable=False)
    health_grade: Mapped[str] = mapped_column(sa.String(1), nullable=False)
    brake_pressure_atm: Mapped[float] = mapped_column(sa.Float, nullable=False)
    error_code: Mapped[str | None] = mapped_column(sa.String(10), nullable=True)
    # ELECTRIC fields
    catenary_voltage_kv: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    transformer_temp_c: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    power_consumption_kw: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    # DIESEL fields
    oil_temp_c: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    fuel_level_liters: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    engine_rpm: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
