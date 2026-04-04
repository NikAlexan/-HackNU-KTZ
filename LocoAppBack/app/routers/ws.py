"""
WebSocket endpoint: ws://host/ws/loco/data

Streams the latest BCK-3 packet produced by the background generator.
Multiple clients can connect simultaneously — all get the same data.
"""
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import app.generator as generator
from app.telemetry.simulation import INTERVAL_MS

router = APIRouter()


@router.websocket("/ws/loco/data")
async def loco_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            if generator.latest_packet is not None:
                await websocket.send_json(generator.latest_packet)
            await asyncio.sleep(INTERVAL_MS / 1000)
    except WebSocketDisconnect:
        pass