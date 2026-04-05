"""
Sensor extraction layer.

Converts the raw simulation state dict into a flat dict of named numeric sensor
readings. This dict is the single input to health calculation, component health
tracking, DB storage (sensors_json), and WebSocket packet assembly.

Rules:
- Only scalar numeric values (int, float) — no lists, no None
- No business logic — pure extraction and rounding
- Meta fields (traction_mode, error_code, etc.) are excluded
"""

# State keys that are metadata, not sensor readings
_META_KEYS: frozenset[str] = frozenset({
    "traction_mode",
    "km_position",
    "error_code",
    "pantograph_up",
    "regen_energy",    # accumulated energy counter, not a rate sensor
    # Raw lists — too large to store per-tick; derived scalars (td_currents_max) are kept
    "td_currents",
    "td_temps",
    "axle_loads",
})


def extract_sensors(state: dict, loco_type: str) -> dict:  # noqa: ARG001
    """
    Return a flat dict of numeric sensor readings extracted from simulation state.

    Args:
        state:     Raw simulation state dict from evolve_state()
        loco_type: "electro" or "diesel" (reserved for future type-specific logic)

    Returns:
        Dict of {sensor_name: numeric_value} — ready for DB storage and health calc.
    """
    result: dict = {}
    for key, value in state.items():
        if key in _META_KEYS:
            continue
        if isinstance(value, float):
            result[key] = round(value, 4)
        elif isinstance(value, int):
            result[key] = value
        # lists, None, bool (pantograph_up excluded via _META_KEYS) → skip
    return result
