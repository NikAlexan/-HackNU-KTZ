"""
WebSocket /ws/locomotives

Streams a summary of all locomotives every 3 seconds:
  - identity + status + health
  - latest 5-minute aggregate metrics
"""
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from sqlalchemy import desc, select

from app.database import AsyncSessionLocal
from app.models import Locomotive, TelemetryAggregate
from app.routers.auth import decode_token

router = APIRouter()

_INTERVAL_SEC = 3


async def _build_summary() -> list[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Locomotive).order_by(Locomotive.id))
        locos = result.scalars().all()

        summary = []
        for loco in locos:
            agg_result = await session.execute(
                select(TelemetryAggregate)
                .where(TelemetryAggregate.loco_id == loco.id)
                .order_by(desc(TelemetryAggregate.period_start))
                .limit(1)
            )
            agg = agg_result.scalar_one_or_none()

            entry: dict = {
                "id": loco.id,
                "series": loco.series,
                "number": loco.number,
                "type": loco.type,
                "status": loco.status,
                "health_index": loco.health_index,
                "health_grade": loco.health_grade,
                "component_health": loco.component_health or {},
                "last_aggregate": None,
            }

            if agg is not None:
                entry["last_aggregate"] = {
                    "period_start": agg.period_start.isoformat(),
                    "period_end": agg.period_end.isoformat(),
                    "avg_speed_kmh": agg.avg_speed_kmh,
                    "avg_health_index": agg.avg_health_index,
                    "final_health_grade": agg.final_health_grade,
                    "readings_count": agg.readings_count,
                    "error_count": agg.error_count,
                    "metrics_json": agg.metrics_json or {},
                }

            summary.append(entry)

    return summary


@router.websocket("/ws/locomotives")
async def locomotives_stream(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        return
    try:
        decode_token(token)
    except Exception:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    try:
        while True:
            summary = await _build_summary()
            await websocket.send_json(summary)
            await asyncio.sleep(_INTERVAL_SEC)
    except WebSocketDisconnect:
        pass
