"""
WebSocket endpoint: ws://host/ws

Streams BCK-3 onboard computer data every 500 ms.
Locomotive identity (id, type, series) is read from env via app.config.
Each reading is persisted to generated_readings for 5-minute aggregation.
"""
import asyncio
import random
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import LOCO_ID, LOCO_SERIES, LOCO_TYPE
from app.database import AsyncSessionLocal
from app.models import GeneratedReading
from app.telemetry.packet import build_packet, state_to_reading
from app.telemetry.simulation import INTERVAL_MS, calculate_health_index, evolve_state, init_state

router = APIRouter()

_TOTAL_STEPS = 7200  # 1 hour @ 500 ms; progress wraps after this

_SCENARIOS = ["NORMAL_RUN", "OVERHEAT", "CRITICAL_ALERT"]
if LOCO_TYPE == "electro":
    _SCENARIOS.append("VOLTAGE_SAG")


@router.websocket("/ws/loco/data")
async def loco_stream(websocket: WebSocket) -> None:
    await websocket.accept()

    scenario = random.choice(_SCENARIOS)
    state = init_state(LOCO_TYPE)
    step = 0

    try:
        while True:
            now = datetime.now(tz=timezone.utc)
            state = evolve_state(state, LOCO_TYPE, scenario, step % _TOTAL_STEPS, _TOTAL_STEPS)
            reading = state_to_reading(state, LOCO_TYPE)
            health_index, health_grade = calculate_health_index(reading, LOCO_TYPE)
            packet = build_packet(LOCO_ID, LOCO_SERIES, LOCO_TYPE, step, state, health_index, health_grade)

            await websocket.send_json(packet)

            async with AsyncSessionLocal() as session:
                session.add(GeneratedReading(
                    loco_id=LOCO_ID,
                    loco_type=LOCO_TYPE,
                    ts=now,
                    speed_kmh=state["speed"],
                    traction_mode=state["traction_mode"],
                    health_index=health_index,
                    health_grade=health_grade,
                    brake_pressure_atm=state["brake"],
                    error_code=state.get("error_code"),
                    catenary_voltage_kv=state.get("catenary_v"),
                    transformer_temp_c=state.get("transformer_temp"),
                    power_consumption_kw=state.get("power_kw"),
                    oil_temp_c=state.get("oil_temp"),
                    fuel_level_liters=state.get("fuel"),
                    engine_rpm=state.get("engine_rpm"),
                ))
                await session.commit()

            step += 1
            await asyncio.sleep(INTERVAL_MS / 1000)
    except WebSocketDisconnect:
        pass
