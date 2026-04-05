from datetime import datetime
from typing import Optional

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
    error_code: Mapped[str | None] = mapped_column(sa.String(10), nullable=True)
    # All sensor readings stored dynamically — no fixed type-specific columns
    sensors_json: Mapped[dict] = mapped_column(sa.JSON, nullable=False, default=dict)
    # Instantaneous component risk per tick — averaged over period in reporter
    component_risks_json: Mapped[dict] = mapped_column(sa.JSON, nullable=False, default=dict)


class ComponentHealth(Base):
    """Persistent cumulative health state per locomotive component node."""

    __tablename__ = "component_health"

    loco_id: Mapped[str] = mapped_column(sa.String(64), primary_key=True)
    component: Mapped[str] = mapped_column(sa.String(64), primary_key=True)
    health: Mapped[float] = mapped_column(sa.Float, nullable=False, default=100.0)
    risk_accum: Mapped[float] = mapped_column(sa.Float, nullable=False, default=0.0)
    last_repair: Mapped[Optional[datetime]] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True),
        server_default=sa.text("now()"),
        onupdate=sa.func.now(),
        nullable=False,
    )
