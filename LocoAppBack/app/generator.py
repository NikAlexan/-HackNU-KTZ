"""
Background generator: continuously evolves locomotive state,
persists readings to DB, and exposes the latest packet for WS clients.

Pipeline per tick:
  evolve_state()         → raw simulation state
  extract_sensors()      → flat numeric sensor dict
  calc_health_from_config() → instantaneous health index + grade
  tracker.tick()         → cumulative component health snapshot
  build_packet()         → JSON for WebSocket clients
  GeneratedReading       → persisted to DB
  tracker.flush()        → every FLUSH_EVERY ticks
"""
import asyncio
import logging
import random
from datetime import datetime, timezone

from app.config import LOCO_ID, LOCO_NODE_CONFIG, LOCO_SERIES, LOCO_TYPE
from app.database import AsyncSessionLocal
from app.models import GeneratedReading
from app.telemetry.health import FLUSH_EVERY, ComponentHealthTracker, calc_health_from_config
from app.telemetry.node_config import load_node_config
from app.telemetry.packet import build_packet
from app.telemetry.sensors_extract import extract_sensors
from app.telemetry.simulation import INTERVAL_MS, evolve_state, init_state

logger = logging.getLogger(__name__)

_TOTAL_STEPS = 7200  # 1 hour @ 500 ms

_SCENARIOS = ["NORMAL_RUN", "OVERHEAT", "CRITICAL_ALERT"]
if LOCO_TYPE == "electro":
    _SCENARIOS.append("VOLTAGE_SAG")

# Shared state — WebSocket clients and maintenance router read from here
latest_packet: dict | None = None
tracker: ComponentHealthTracker | None = None


async def run_generator() -> None:
    global latest_packet, tracker

    scenario = random.choice(_SCENARIOS)
    state = init_state(LOCO_TYPE)
    step = 0
    dt_sec = INTERVAL_MS / 1000

    logger.info("Generator started — scenario: %s", scenario)

    node_cfg = load_node_config(LOCO_NODE_CONFIG, LOCO_TYPE)
    async with AsyncSessionLocal() as session:
        tracker = await ComponentHealthTracker.load(session, LOCO_ID, node_cfg)

    while True:
        now = datetime.now(tz=timezone.utc)

        # 1. Physics
        state = evolve_state(state, LOCO_TYPE, scenario, step % _TOTAL_STEPS, _TOTAL_STEPS)

        # 2. Sensor extraction — flat dict, single source of truth for all downstream
        sensors = extract_sensors(state, LOCO_TYPE)

        # 3. Instantaneous health (config-driven, no hardcoded thresholds)
        health_index, health_grade = calc_health_from_config(sensors, node_cfg)

        # 4. Cumulative component health
        component_snap = tracker.tick(sensors, dt_sec)
        component_risks = tracker.current_risks(sensors)

        # 5. WebSocket packet
        packet = build_packet(
            LOCO_ID, LOCO_SERIES, LOCO_TYPE, step, state, sensors,
            health_index, health_grade, component_snap, component_risks,
        )
        latest_packet = packet

        # 6. Persist reading + periodic health flush
        async with AsyncSessionLocal() as session:
            session.add(GeneratedReading(
                loco_id=LOCO_ID,
                loco_type=LOCO_TYPE,
                ts=now,
                speed_kmh=state["speed"],
                traction_mode=state["traction_mode"],
                health_index=health_index,
                health_grade=health_grade,
                error_code=state.get("error_code"),
                sensors_json=sensors,
            ))
            await session.commit()

            if step % FLUSH_EVERY == 0:
                await tracker.flush(session)

        step += 1
        await asyncio.sleep(dt_sec)
