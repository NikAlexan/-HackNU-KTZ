"""
Sensor subsystem definitions for the onboard computer (BCK-3).

Three sensors:
  OVERHEAT       — transformer temp (ELECTRIC) / oil temp (DIESEL)
  VOLTAGE        — catenary voltage, ELECTRIC only
  BRAKE_PRESSURE — brake pipe pressure, all types
"""


def temp_sensor(value: float, label: str) -> dict:
    if value >= 95.0:
        status = "CRIT"
    elif value >= 85.0:
        status = "WARN"
    else:
        status = "OK"
    return {
        "id": "SNS-TEMP",
        "label": label,
        "value": round(value, 1),
        "unit": "°C",
        "warn_threshold": 85.0,
        "crit_threshold": 95.0,
        "status": status,
    }


def voltage_sensor(value: float) -> dict:
    if value <= 20.0:
        status = "CRIT"
    elif value <= 23.0:
        status = "WARN"
    else:
        status = "OK"
    return {
        "id": "SNS-VOLT",
        "label": "Напряжение КС",
        "value": round(value, 2),
        "unit": "кВ",
        "warn_threshold": 23.0,
        "crit_threshold": 20.0,
        "status": status,
    }


def brake_pressure_sensor(value: float) -> dict:
    if value < 3.5 or value > 6.5:
        status = "CRIT"
    elif value < 4.5 or value > 6.0:
        status = "WARN"
    else:
        status = "OK"
    return {
        "id": "SNS-BP",
        "label": "Давление ТМ",
        "value": round(value, 2),
        "unit": "атм",
        "warn_threshold_lo": 4.5,
        "warn_threshold_hi": 6.0,
        "crit_threshold_lo": 3.5,
        "crit_threshold_hi": 6.5,
        "status": status,
    }


def build_sensors(state: dict, loco_type: str) -> dict:
    sensors: dict = {}
    if loco_type == "electro":
        sensors["OVERHEAT"] = temp_sensor(state["transformer_temp"], "Температура трансформатора")
        sensors["VOLTAGE"] = voltage_sensor(state["catenary_v"])
    else:
        sensors["OVERHEAT"] = temp_sensor(state["oil_temp"], "Температура масла")
    sensors["BRAKE_PRESSURE"] = brake_pressure_sensor(state["brake"])
    return sensors
