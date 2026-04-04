"""
GET /api/locomotives          — list all with health
GET /api/locomotives/{id}     — details + recent aggregates
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Locomotive, TelemetryAggregate

router = APIRouter()


@router.get("/locomotives")
async def list_locomotives(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(select(Locomotive).order_by(Locomotive.id))
    locos = result.scalars().all()
    return [
        {
            "id": loco.id,
            "series": loco.series,
            "number": loco.number,
            "type": loco.type,
            "driver": loco.driver,
            "status": loco.status,
            "health_index": loco.health_index,
            "health_grade": loco.health_grade,
            "route_id": loco.route_id,
        }
        for loco in locos
    ]


@router.get("/locomotives/{loco_id}")
async def get_locomotive(
    loco_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    loco = await session.get(Locomotive, loco_id)
    if loco is None:
        raise HTTPException(status_code=404, detail="Locomotive not found")

    agg_result = await session.execute(
        select(TelemetryAggregate)
        .where(TelemetryAggregate.loco_id == loco_id)
        .order_by(desc(TelemetryAggregate.period_start))
        .limit(12)
    )
    aggregates = agg_result.scalars().all()

    return {
        "id": loco.id,
        "series": loco.series,
        "number": loco.number,
        "type": loco.type,
        "driver": loco.driver,
        "status": loco.status,
        "health_index": loco.health_index,
        "health_grade": loco.health_grade,
        "route_id": loco.route_id,
        "recent_aggregates": [
            {
                "period_start": a.period_start,
                "period_end": a.period_end,
                "avg_speed_kmh": a.avg_speed_kmh,
                "max_temp_c": a.max_temp_c,
                "min_voltage_kv": a.min_voltage_kv,
                "avg_health_index": a.avg_health_index,
                "final_health_grade": a.final_health_grade,
                "error_count": a.error_count,
            }
            for a in aggregates
        ],
    }
