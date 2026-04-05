"""
POST /api/locomotives/register — one-time registration from loco-app (Bearer protected)
GET  /api/locomotives          — list all with health
GET  /api/locomotives/{id}     — details + recent aggregates
"""
from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Locomotive, LocoStatus, LocoType, TelemetryAggregate
from app.routers.ingest import _API_KEY
from app.routers.auth import require_user

router = APIRouter()

_bearer = HTTPBearer()

_TYPE_MAP = {"electro": LocoType.ELECTRIC, "diesel": LocoType.DIESEL}


def _verify_token(creds: HTTPAuthorizationCredentials = Security(_bearer)) -> None:
    if creds.credentials != _API_KEY:
        raise HTTPException(status_code=401, detail="Invalid token")


class RegisterPayload(BaseModel):
    loco_id: str
    loco_type: str
    loco_series: str


@router.post("/locomotives/register", status_code=200, dependencies=[Depends(_verify_token)])
async def register_locomotive(
    payload: RegisterPayload,
    session: AsyncSession = Depends(get_session),
) -> dict:
    existing = await session.get(Locomotive, payload.loco_id)
    if existing:
        return {"status": "already_registered"}

    loco_type = _TYPE_MAP.get(payload.loco_type.lower())
    if loco_type is None:
        raise HTTPException(status_code=422, detail=f"Unknown loco_type: {payload.loco_type}")

    session.add(Locomotive(
        id=payload.loco_id,
        series=payload.loco_series,
        number=payload.loco_id,
        type=loco_type,
        driver="Unknown",
        status=LocoStatus.STOPPED,
        health_index=100.0,
        health_grade="A",
    ))
    await session.commit()
    return {"status": "registered"}



@router.get("/locomotives")
async def list_locomotives(
    session: AsyncSession = Depends(get_session),
    _: str = Depends(require_user),
) -> list[dict]:
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
            "component_health": loco.component_health or {},
            "component_risks": loco.component_risks or {},
            "route_id": loco.route_id,
        }
        for loco in locos
    ]


@router.get("/locomotives/{loco_id}")
async def get_locomotive(
    loco_id: str,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(require_user),
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
        "component_health": loco.component_health or {},
        "component_risks": loco.component_risks or {},
        "route_id": loco.route_id,
        "recent_aggregates": [
            {
                "period_start": a.period_start,
                "period_end": a.period_end,
                "avg_speed_kmh": a.avg_speed_kmh,
                "avg_health_index": a.avg_health_index,
                "final_health_grade": a.final_health_grade,
                "error_count": a.error_count,
                "metrics_json": a.metrics_json or {},
            }
            for a in aggregates
        ],
    }
