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
from app.database import AsyncSessionLocal  # used by ComponentHealthTracker.load
from app.telemetry.health import ComponentHealthTracker, health_grade_from_index
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
active_scenario: str | None = None  # overridden via /api/maintenance/incident


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

        # 1. Physics — use overridden scenario if set
        # When forced, use step=5500 so all time-gated effects are already active
        # (OVERHEAT kicks in at t>=1800s → step>=3600; CRITICAL_ALERT at t>=2700s → step>=5400)
        current = active_scenario if active_scenario is not None else scenario
        sim_step = 5500 if active_scenario is not None else step % _TOTAL_STEPS
        state = evolve_state(state, LOCO_TYPE, current, sim_step, _TOTAL_STEPS)

        # 2. Sensor extraction — flat dict, single source of truth for all downstream
        sensors = extract_sensors(state, LOCO_TYPE)

        # 3+4. Risks computed once for damage + display; health_index from cumulative snap
        component_snap, component_risks = tracker.tick(sensors, dt_sec)
        components_cfg = node_cfg["components"]
        total_w, weighted_h = 0.0, 0.0
        for name, h in component_snap.items():
            w = float(components_cfg[name].get("weight", 1.0))
            weighted_h += h * w
            total_w += w
        health_index = round(weighted_h / total_w, 1) if total_w else 100.0
        health_grade = health_grade_from_index(health_index)

        # 5. WebSocket packet
        packet = build_packet(
            LOCO_ID, LOCO_SERIES, LOCO_TYPE, step, state, sensors,
            health_index, health_grade, component_snap, component_risks,
        )
        latest_packet = packet

        step += 1
        await asyncio.sleep(dt_sec)
