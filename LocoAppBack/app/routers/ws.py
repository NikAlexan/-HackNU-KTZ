"""
WebSocket endpoint: ws://host/ws/loco/data

One background task broadcasts the latest BCK-3 packet to all connected
clients every INTERVAL_MS. DB is not touched here — packet comes from
the in-memory generator.latest_packet.
"""
import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import app.generator as generator
from app.telemetry.simulation import INTERVAL_MS

router = APIRouter()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Broadcaster
# ---------------------------------------------------------------------------

_clients: set[WebSocket] = set()
_broadcast_task: asyncio.Task | None = None


async def _broadcaster() -> None:
    """Single loop: read latest_packet once, send to all clients."""
    while True:
        await asyncio.sleep(INTERVAL_MS / 1000)
        if not _clients or generator.latest_packet is None:
            continue

        message = json.dumps(generator.latest_packet, default=str)
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

@router.websocket("/ws/loco/data")
async def loco_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    _ensure_broadcaster()
    _clients.add(websocket)

    # Send current packet immediately on connect
    if generator.latest_packet is not None:
        try:
            await websocket.send_text(json.dumps(generator.latest_packet, default=str))
        except Exception:
            _clients.discard(websocket)
            return

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(websocket)
