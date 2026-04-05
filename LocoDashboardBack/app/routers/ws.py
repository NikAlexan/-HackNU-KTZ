"""
WebSocket /ws/locomotives

One background task builds the summary once every 3 seconds and broadcasts
it to all connected clients. DB is queried once per tick regardless of how
many clients are connected.
"""
import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from sqlalchemy import desc, select

from app.database import AsyncSessionLocal
from app.models import Locomotive, TelemetryAggregate
from app.routers.auth import decode_token

router = APIRouter()
logger = logging.getLogger(__name__)

_INTERVAL_SEC = 3

# ---------------------------------------------------------------------------
# Broadcaster — shared state
# ---------------------------------------------------------------------------

_clients: set[WebSocket] = set()
_broadcast_task: asyncio.Task | None = None


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
                "component_risks": loco.component_risks or {},
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


async def _broadcaster() -> None:
    """Single loop: query DB once, send to all clients."""
    while True:
        await asyncio.sleep(_INTERVAL_SEC)
        if not _clients:
            continue
        try:
            summary = await _build_summary()
            message = json.dumps(summary, default=str)
        except Exception as exc:
            logger.warning("Broadcaster failed to build summary: %s", exc)
            continue

        dead: set[WebSocket] = set()
        for ws in list(_clients):
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)

        _clients.difference_update(dead)


def _ensure_broadcaster() -> None:
    global _broadcast_task
    if _broadcast_task is None or _broadcast_task.done():
        _broadcast_task = asyncio.create_task(_broadcaster())


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

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
    _ensure_broadcaster()
    _clients.add(websocket)

    # Send current state immediately on connect — don't wait for next tick
    try:
        summary = await _build_summary()
        await websocket.send_text(json.dumps(summary, default=str))
    except Exception:
        _clients.discard(websocket)
        return

    try:
        # Keep connection alive — broadcaster pushes updates
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(websocket)
