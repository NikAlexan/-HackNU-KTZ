"""
BCK-3 packet assembly.

Assembles the JSON payload sent over WebSocket to dashboard clients.
Accepts the flat sensors dict from extract_sensors() — no direct knowledge
of the simulation state structure.

Legacy helpers (state_to_reading, calculate_health_index) are removed;
health calculation is now in health.py.
"""
from datetime import datetime, timezone

from app.telemetry.sensors import build_sensors


def _overall_health(component_snap: dict[str, float]) -> float:
    if not component_snap:
        return 100.0
    return round(sum(component_snap.values()) / len(component_snap), 1)


def build_packet(
    loco_id: str,
    series: str,
    loco_type: str,
    step: int,
    state: dict,              # raw state — for metadata and array fields (td_currents, axle_loads)
    sensors: dict,            # flat sensor readings from extract_sensors()
    health_index: float,
    health_grade: str,
    component_health: dict[str, float] | None = None,
    component_risks: dict[str, float] | None = None,
) -> dict:
    packet: dict = {
        # BCK header
        "source": "BCK-3",
        "loco_id": loco_id,
        "type": loco_type,
        "series": series,
        "ts": datetime.now(tz=timezone.utc).isoformat(),
        "step": step,
        # Traction metadata
        "speed": round(state["speed"], 1),
        "traction_mode": state["traction_mode"],
        "km_position": state["km_position"],
        "error_code": state.get("error_code"),
        # Health
        "health_index": health_index,
        "health_grade": health_grade,
        "component_health": component_health or {},
        "component_risks": component_risks or {},
        "overall_health": _overall_health(component_health or {}),
        # All scalar sensor readings (from sensors_extract)
        "sensors": sensors,
        # Legacy sensor subsystem display (thresholds + status labels)
        "sensor_systems": build_sensors(state, loco_type),
    }

    # Array fields (not stored in sensors_json due to size — included in WS packet only)
    if loco_type == "electro":
        packet["td_currents_a"] = [round(c, 1) for c in state["td_currents"]]
        packet["td_temps_c"] = [round(t, 1) for t in state["td_temps"]]
        packet["pantograph_up"] = state.get("pantograph_up", True)
        packet["regen_energy_kwh"] = round(state["regen_energy"], 3)
    else:
        packet["axle_loads_t"] = [round(a, 2) for a in state["axle_loads"]]

    return packet
