"""
BCK-3 packet assembly.

Converts simulation state + health metrics into the JSON payload
sent to the WebSocket client.
"""
from datetime import datetime, timezone

from app.telemetry.sensors import build_sensors


def state_to_reading(state: dict, loco_type: str) -> dict:
    """Flatten simulation state into the dict format expected by calculate_health_index."""
    r: dict = {
        "brake_pressure_atm": state["brake"],
        "error_code": state.get("error_code"),
    }
    if loco_type == "electro":
        r["transformer_temp_c"] = state["transformer_temp"]
        r["catenary_voltage_kv"] = state["catenary_v"]
        for i, c in enumerate(state["td_currents"], 1):
            r[f"td{i}_current_a"] = c
    else:
        r["oil_temp_c"] = state["oil_temp"]
        r["fuel_level_liters"] = state["fuel"]
    return r


def build_packet(
    loco_id: str,
    series: str,
    loco_type: str,
    step: int,
    state: dict,
    health_index: float,
    health_grade: str,
) -> dict:
    packet: dict = {
        # BCK header
        "source": "BCK-3",
        "loco_id": loco_id,
        "type": loco_type,
        "series": series,
        "ts": datetime.now(tz=timezone.utc).isoformat(),
        "step": step,
        # Traction parameters
        "speed": round(state["speed"], 1),
        "traction_mode": state["traction_mode"],
        "km_position": state["km_position"],
        "battery_v": state["battery"],
        "pressure": state["brake"],
        # Health
        "health_index": health_index,
        "health_grade": health_grade,
        "error_code": state.get("error_code"),
        # Sensor subsystems
        "sensors": build_sensors(state, loco_type),
    }

    if loco_type == "electro":
        packet.update(
            {
                "catenary_voltage_kv": state["catenary_v"],
                "pantograph_current_a": state.get("pantograph_current"),
                "power_consumption_kw": state.get("power_kw"),
                "regen_power_kw": state.get("regen_power"),
                "power_factor": state.get("power_factor"),
                "transformer_temp_c": state["transformer_temp"],
                "td_currents_a": [round(c, 1) for c in state["td_currents"]],
                "td_temps_c": [round(t, 1) for t in state["td_temps"]],
                "pantograph_up": state.get("pantograph_up", True),
                "regen_energy_kwh": round(state["regen_energy"], 3),
            }
        )
    else:
        packet.update(
            {
                "fuel": round(state["fuel"], 1),
                "fuel_consumption_lh": state.get("fuel_consumption"),
                "engine_rpm": state["engine_rpm"],
                "oil_temp_c": state["oil_temp"],
                "coolant_temp_c": state["coolant_temp"],
                "oil_pressure_bar": state["oil_pressure"],
                "traction_force_kn": state.get("traction_force"),
                "main_gen_voltage_v": state.get("main_gen_v"),
                "axle_loads_t": [round(a, 2) for a in state["axle_loads"]],
            }
        )

    return packet
