"""
POST /api/telemetry/aggregate
Receives 5-minute aggregate reports from loco-app.
Protected by Bearer token (API_KEY env var).
"""
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import HealthGrade, Locomotive, LocoStatus, TelemetryAggregate

router = APIRouter()

_bearer = HTTPBearer()
_API_KEY = os.environ["API_KEY"]


def _verify_token(creds: HTTPAuthorizationCredentials = Security(_bearer)) -> None:
    if creds.credentials != _API_KEY:
        raise HTTPException(status_code=401, detail="Invalid token")


class LocoAggregate(BaseModel):
    loco_id: str
    loco_type: str
    readings_count: int
    avg_speed_kmh: float
    avg_health_index: float
    final_health_grade: HealthGrade
    error_count: int
    component_health: dict | None = None
    component_risks: dict | None = None
    metrics_json: dict | None = None
    # Legacy fields — kept optional for backward compatibility
    max_temp_c: float | None = None
    min_voltage_kv: float | None = None


class AggregatePayload(BaseModel):
    period_start: datetime
    period_end: datetime
    locomotives: list[LocoAggregate]


@router.post(
    "/telemetry/aggregate",
    status_code=204,
    dependencies=[Depends(_verify_token)],
)
async def receive_aggregate(
    payload: AggregatePayload,
    session: AsyncSession = Depends(get_session),
) -> None:
    for loco in payload.locomotives:
        session.add(
            TelemetryAggregate(
                loco_id=loco.loco_id,
                loco_type=loco.loco_type,
                period_start=payload.period_start,
                period_end=payload.period_end,
                readings_count=loco.readings_count,
                avg_speed_kmh=loco.avg_speed_kmh,
                max_temp_c=loco.max_temp_c or 0.0,
                min_voltage_kv=loco.min_voltage_kv,
                avg_health_index=loco.avg_health_index,
                final_health_grade=loco.final_health_grade,
                error_count=loco.error_count,
                metrics_json=loco.metrics_json,
            )
        )

        db_loco = await session.get(Locomotive, loco.loco_id)
        if db_loco is not None:
            db_loco.status = LocoStatus.IN_MOTION if loco.avg_speed_kmh > 1.0 else LocoStatus.STOPPED
            db_loco.health_index = loco.avg_health_index
            db_loco.health_grade = HealthGrade(loco.final_health_grade)
            if loco.component_health is not None:
                db_loco.component_health = loco.component_health
            if loco.component_risks is not None:
                db_loco.component_risks = loco.component_risks

    await session.commit()
