"""
Deterministic seeder for locomotive_telemetry DB.
Fleet: 7 KZ8A (ELECTRIC) + 5 ТЭ33А (DIESEL) = 12 locomotives
Telemetry: 1 hour, 500ms interval per loco = 7 200 readings each (~86 400 total)
Run: python seed.py
"""
import os
import random
import sys
from datetime import datetime, timedelta, timezone

import psycopg2
import psycopg2.extras

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

random.seed(42)

BASE_TS = datetime(2026, 4, 4, 6, 0, 0, tzinfo=timezone.utc)
HOURS = 1
INTERVAL_MS = 500
TOTAL_STEPS = int(HOURS * 3600 * 1000 / INTERVAL_MS)  # 7200

_raw_url = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://loco_user:loco_pass@localhost:5432/locomotive_telemetry",
)
# Strip +asyncpg driver prefix for psycopg2
DSN = _raw_url.replace("postgresql+asyncpg://", "postgresql://")

# ---------------------------------------------------------------------------
# Static data
# ---------------------------------------------------------------------------

ROUTES = [
    {
        "id": "route-ast-kks",
        "from_station": "Нур-Султан",
        "to_station": "Кокшетау",
        "total_km": 305.0,
        "electrified": True,
        "schedule_departure": BASE_TS,
        "schedule_arrival": BASE_TS + timedelta(hours=3, minutes=30),
    },
    {
        "id": "route-kks-ptr",
        "from_station": "Кокшетау",
        "to_station": "Петропавловск",
        "total_km": 160.0,
        "electrified": True,
        "schedule_departure": BASE_TS + timedelta(hours=4),
        "schedule_arrival": BASE_TS + timedelta(hours=6),
    },
    {
        "id": "route-ast-ptr",
        "from_station": "Нур-Султан",
        "to_station": "Петропавловск",
        "total_km": 465.0,
        "electrified": True,
        "schedule_departure": BASE_TS,
        "schedule_arrival": BASE_TS + timedelta(hours=5, minutes=30),
    },
    {
        "id": "route-kks-depot",
        "from_station": "Кокшетау",
        "to_station": "Кокшетау (депо)",
        "total_km": 0.0,
        "electrified": False,
        "schedule_departure": BASE_TS,
        "schedule_arrival": BASE_TS + timedelta(minutes=30),
    },
]

WAYPOINTS = [
    # route-ast-kks
    {"route_id": "route-ast-kks", "name": "Нур-Султан", "km_mark": 0.0, "lat": 51.18, "lon": 71.45, "speed_limit_kmh": 80},
    {"route_id": "route-ast-kks", "name": "Макинск", "km_mark": 150.0, "lat": 52.63, "lon": 70.86, "speed_limit_kmh": 100},
    {"route_id": "route-ast-kks", "name": "Кокшетау", "km_mark": 305.0, "lat": 53.28, "lon": 69.39, "speed_limit_kmh": 60},
    # route-kks-ptr
    {"route_id": "route-kks-ptr", "name": "Кокшетау", "km_mark": 0.0, "lat": 53.28, "lon": 69.39, "speed_limit_kmh": 60},
    {"route_id": "route-kks-ptr", "name": "Петропавловск", "km_mark": 160.0, "lat": 54.87, "lon": 69.16, "speed_limit_kmh": 80},
    # route-ast-ptr
    {"route_id": "route-ast-ptr", "name": "Нур-Султан", "km_mark": 0.0, "lat": 51.18, "lon": 71.45, "speed_limit_kmh": 80},
    {"route_id": "route-ast-ptr", "name": "Кокшетау", "km_mark": 305.0, "lat": 53.28, "lon": 69.39, "speed_limit_kmh": 60},
    {"route_id": "route-ast-ptr", "name": "Петропавловск", "km_mark": 465.0, "lat": 54.87, "lon": 69.16, "speed_limit_kmh": 80},
    # route-kks-depot
    {"route_id": "route-kks-depot", "name": "Кокшетау (депо)", "km_mark": 0.0, "lat": 53.28, "lon": 69.38, "speed_limit_kmh": 20},
]

DRIVERS = [
    "Алтынбеков Р.М.", "Сейткали Д.А.", "Жаксыбеков Н.Т.",
    "Байжанов С.К.", "Нурмаганбетов А.Р.", "Ергалиев М.Б.",
    "Кусаинов Т.Ж.", "Ахметов Е.Д.", "Темиров О.Н.",
    "Сатыбалдиев Б.А.", "Кожахметов В.К.", "Джаксыбеков Р.С.",
]

FLEET_SPEC = [
    # (series, id_prefix, loco_type, count, route_id)
    ("KZ8A",  "kz8a",  "ELECTRIC", 4, "route-ast-kks"),
    ("KZ8A",  "kz8a",  "ELECTRIC", 3, "route-kks-ptr"),
    ("ТЭ33А", "te33a", "DIESEL",   3, "route-ast-kks"),
    ("ТЭ33А", "te33a", "DIESEL",   2, "route-kks-ptr"),
]

SCENARIOS = ["NORMAL_RUN", "OVERHEAT", "VOLTAGE_SAG", "CRITICAL_ALERT"]

# Guaranteed coverage — at least one of each scenario type
SCENARIO_POOL = ["NORMAL_RUN"] * 7 + ["OVERHEAT", "VOLTAGE_SAG", "CRITICAL_ALERT"] + ["NORMAL_RUN"]
random.shuffle(SCENARIO_POOL)

# ---------------------------------------------------------------------------
# Health index calculation
# ---------------------------------------------------------------------------

def calculate_health_index(reading: dict, loco_type: str) -> tuple[float, str]:
    penalties = 0.0

    # Temperature
    temp = reading.get("oil_temp_c") or reading.get("transformer_temp_c") or 0.0
    if temp > 95:
        penalties += 25.0
    elif temp > 80:
        penalties += 25.0 * (temp - 80.0) / 15.0

    # Catenary voltage (ELECTRIC only)
    if loco_type == "ELECTRIC":
        v = reading.get("catenary_voltage_kv") or 25.0
        if v < 20:
            penalties += 20.0
        elif v < 23:
            penalties += 20.0 * (23.0 - v) / 3.0

    # Max TD current (8 motors for KZ8A, 4 for ТЭ33А uses td1-td4)
    td_currents = [
        reading.get(f"td{i}_current_a") or 0.0
        for i in range(1, 9)
    ]
    max_td = max(td_currents)
    if max_td > 650:
        penalties += 20.0
    elif max_td > 550:
        penalties += 20.0 * (max_td - 550.0) / 100.0

    # Brake pressure
    bp = reading.get("brake_pressure_atm", 5.0) or 5.0
    if bp < 3.5 or bp > 6.5:
        penalties += 20.0
    elif bp < 4.5:
        penalties += 20.0 * (4.5 - bp) / 1.0
    elif bp > 6.0:
        penalties += 20.0 * (bp - 6.0) / 0.5

    # Fuel level (DIESEL only)
    if loco_type == "DIESEL":
        fuel = reading.get("fuel_level_liters") or 8000.0
        pct = fuel / 16000.0
        if pct < 0.20:
            penalties += 10.0
        elif pct < 0.40:
            penalties += 10.0 * (0.40 - pct) / 0.20

    # Error code
    ec = reading.get("error_code")
    if ec:
        if ec[-1] in ("1", "2"):
            penalties += 5.0
        else:
            penalties += 2.5

    index = max(0.0, round(100.0 - penalties, 1))
    if index >= 90:
        grade = "A"
    elif index >= 75:
        grade = "B"
    elif index >= 60:
        grade = "C"
    elif index >= 40:
        grade = "D"
    else:
        grade = "E"
    return index, grade


# ---------------------------------------------------------------------------
# Telemetry simulation
# ---------------------------------------------------------------------------

def _gauss(mu: float, sigma: float) -> float:
    return random.gauss(mu, sigma)


def init_state(loco_type: str) -> dict:
    if loco_type == "ELECTRIC":
        return {
            "speed": 0.0,
            "brake": 5.2,
            "battery": 110.0,
            "catenary_v": 25.0,
            "transformer_temp": 45.0,
            "td_currents": [350.0] * 8,
            "td_temps": [55.0] * 8,
            "pantograph_up": True,
            "regen_energy": 0.0,
            "error_code": None,
        }
    else:
        return {
            "speed": 0.0,
            "brake": 5.2,
            "battery": 110.0,
            "fuel": 12000.0 + _gauss(0, 500),
            "engine_rpm": 450.0,
            "oil_temp": 62.0,
            "coolant_temp": 60.0,
            "oil_pressure": 5.5,
            "main_gen_v": 540.0,
            "traction_force": 0.0,
            "axle_loads": [18.0, 18.0, 18.0, 18.0],
            "error_code": None,
        }


def evolve_state(
    state: dict,
    loco_type: str,
    scenario: str,
    step: int,
    total_steps: int,
) -> dict:
    s = state.copy()
    if loco_type == "ELECTRIC":
        s["td_currents"] = list(state["td_currents"])
        s["td_temps"] = list(state["td_temps"])
        s["axle_loads"] = None
    else:
        s["axle_loads"] = list(state["axle_loads"])

    dt_min = INTERVAL_MS / 1000 / 60  # minutes per step
    progress = step / total_steps  # 0.0 → 1.0
    t_sec = step * INTERVAL_MS / 1000  # seconds since start

    # --- Speed profile ---
    if progress < 0.15:
        target_speed = 120.0 * (progress / 0.15)
    elif progress < 0.85:
        target_speed = 120.0
    else:
        target_speed = 120.0 * (1.0 - (progress - 0.85) / 0.15)
    s["speed"] = max(0.0, target_speed + _gauss(0, 1.5))

    # Traction mode
    if progress < 0.15:
        traction_mode = "TRACTION"
    elif progress > 0.85:
        traction_mode = "BRAKE"
    else:
        traction_mode = "TRACTION" if s["speed"] > 5 else "IDLE"

    # Brake pressure
    if traction_mode == "BRAKE":
        s["brake"] = min(6.2, state["brake"] + _gauss(0.05, 0.01))
    else:
        s["brake"] = max(4.6, state["brake"] + _gauss(-0.01, 0.01))
    s["brake"] = round(max(3.0, min(7.0, s["brake"])), 2)

    # Battery
    s["battery"] = round(109.0 + _gauss(0, 0.5), 1)

    # km_position (rough approximation)
    km_position = int(progress * 15)

    # --- ELECTRIC specifics ---
    if loco_type == "ELECTRIC":
        # Catenary voltage
        catenary_v = 25.0 + _gauss(0, 0.15)
        if scenario == "VOLTAGE_SAG" and 900 <= t_sec <= 1080:
            drop = (t_sec - 900) / 180 * 2.5
            catenary_v = 25.0 - drop + _gauss(0, 0.05)
        s["catenary_v"] = round(max(18.0, min(29.0, catenary_v)), 2)

        # Power and current
        speed_factor = s["speed"] / 120.0
        power_kw = speed_factor * 5520.0 + _gauss(0, 50)
        pantograph_current = power_kw / (s["catenary_v"] * 1.0) if s["catenary_v"] > 0 else 0
        s["pantograph_current"] = round(max(0.0, pantograph_current), 1)

        # Transformer temperature
        load_factor = s["pantograph_current"] / 500.0
        dT = (load_factor * 2.0 - 0.8) * dt_min
        if scenario == "OVERHEAT" and t_sec >= 1800:
            dT += 0.08
        new_temp = state["transformer_temp"] + dT + _gauss(0, 0.05)
        s["transformer_temp"] = round(max(35.0, min(120.0, new_temp)), 1)

        # TD currents & temps (8 motors)
        for i in range(8):
            base_i = 300 + speed_factor * 200 + _gauss(0, 10)
            s["td_currents"][i] = round(max(0.0, base_i), 1)
            dT_td = (s["td_currents"][i] / 450 * 1.5 - 0.6) * dt_min
            new_td_temp = state["td_temps"][i] + dT_td + _gauss(0, 0.05)
            s["td_temps"][i] = round(max(30.0, min(120.0, new_td_temp)), 1)

        # Regen
        if traction_mode == "BRAKE" and s["speed"] > 10:
            traction_mode = "REGEN"
            regen_power = speed_factor * 2500 + _gauss(0, 50)
            s["regen_energy"] = state["regen_energy"] + regen_power * (INTERVAL_MS / 1000) / 3600
        else:
            regen_power = 0.0
            s["regen_energy"] = state["regen_energy"]

        s["power_kw"] = round(max(0.0, power_kw), 1)
        s["regen_power"] = round(max(0.0, regen_power), 1)
        s["power_factor"] = round(0.90 + _gauss(0, 0.01), 3)
        if scenario == "VOLTAGE_SAG" and 900 <= t_sec <= 1080:
            s["power_factor"] = round(max(0.75, s["power_factor"] - 0.08), 3)

        # Errors
        s["error_code"] = None
        if scenario == "VOLTAGE_SAG" and s["catenary_v"] < 23.0:
            s["error_code"] = "E021"
        elif scenario == "OVERHEAT" and s["transformer_temp"] > 90:
            s["error_code"] = "E041"
        elif scenario == "CRITICAL_ALERT" and t_sec >= 2700:
            s["transformer_temp"] = min(110.0, s["transformer_temp"] + 0.5)
            s["error_code"] = "E041"

        s["traction_mode"] = traction_mode

    # --- DIESEL specifics ---
    else:
        speed_factor = s["speed"] / 120.0
        s["engine_rpm"] = round(400 + speed_factor * 650 + _gauss(0, 10), 0)

        fuel_rate = 150 + speed_factor * 450 + _gauss(0, 10)
        s["fuel"] = max(300.0, state["fuel"] - fuel_rate * (INTERVAL_MS / 1000) / 3600)
        s["fuel_consumption"] = round(max(0.0, fuel_rate), 1)

        dT_oil = (speed_factor * 1.5 - 0.5) * dt_min
        if scenario == "OVERHEAT" and t_sec >= 1800:
            dT_oil += 0.08
        s["oil_temp"] = round(max(55.0, min(115.0, state["oil_temp"] + dT_oil + _gauss(0, 0.05))), 1)

        dT_cool = (speed_factor * 1.2 - 0.45) * dt_min
        s["coolant_temp"] = round(max(50.0, min(110.0, state["coolant_temp"] + dT_cool + _gauss(0, 0.05))), 1)

        s["oil_pressure"] = round(max(1.5, min(8.0, 5.5 + _gauss(0, 0.1))), 2)
        s["main_gen_v"] = round(480 + speed_factor * 120 + _gauss(0, 5), 1)
        s["traction_force"] = round(max(0.0, speed_factor * 280 + _gauss(0, 5)), 1)

        for i in range(4):
            s["axle_loads"][i] = round(17.5 + _gauss(0, 0.3), 2)

        s["error_code"] = None
        if scenario == "OVERHEAT" and s["oil_temp"] > 90:
            s["error_code"] = "E011"
        elif scenario == "CRITICAL_ALERT" and t_sec >= 2700:
            s["oil_temp"] = min(110.0, s["oil_temp"] + 0.5)
            s["error_code"] = "E011"

        s["traction_mode"] = traction_mode

    return s


def generate_telemetry(
    loco_id: str,
    loco_type: str,
    scenario: str,
) -> tuple[list[tuple], dict, list[dict]]:
    """Returns (rows_for_db, final_state, events_list)."""
    state = init_state(loco_type)
    rows = []
    events = []
    event_counter = 0

    TELEMETRY_COLS = (
        "loco_id", "ts", "speed_kmh", "brake_pressure_atm", "battery_v",
        "km_position", "traction_mode", "error_code", "is_burst",
        "catenary_voltage_kv", "pantograph_current_a", "power_consumption_kw",
        "regen_power_kw", "power_factor", "transformer_temp_c",
        "td1_current_a", "td2_current_a", "td3_current_a", "td4_current_a",
        "td5_current_a", "td6_current_a", "td7_current_a", "td8_current_a",
        "td1_temp_c", "td2_temp_c", "td3_temp_c", "td4_temp_c",
        "td5_temp_c", "td6_temp_c", "td7_temp_c", "td8_temp_c",
        "pantograph_up", "regen_energy_kwh",
        "fuel_level_liters", "fuel_consumption_lh", "engine_rpm",
        "oil_temp_c", "coolant_temp_c", "oil_pressure_bar",
        "traction_force_kn", "main_gen_voltage_v",
        "axle1_load_t", "axle2_load_t", "axle3_load_t", "axle4_load_t",
    )

    for step in range(TOTAL_STEPS):
        state = evolve_state(state, loco_type, scenario, step, TOTAL_STEPS)
        ts = BASE_TS + timedelta(milliseconds=step * INTERVAL_MS)

        # Burst window: inject 30 seconds at t=3600s with is_burst=True
        is_burst = (3600 <= step * INTERVAL_MS / 1000 < 3630)

        km_pos = int((step / TOTAL_STEPS) * 15)

        if loco_type == "ELECTRIC":
            row = (
                loco_id, ts,
                round(state["speed"], 1),
                state["brake"],
                state["battery"],
                km_pos,
                state["traction_mode"],
                state["error_code"],
                is_burst,
                # ELECTRIC
                state["catenary_v"],
                state["pantograph_current"],
                state["power_kw"],
                state["regen_power"],
                state["power_factor"],
                state["transformer_temp"],
                state["td_currents"][0], state["td_currents"][1],
                state["td_currents"][2], state["td_currents"][3],
                state["td_currents"][4], state["td_currents"][5],
                state["td_currents"][6], state["td_currents"][7],
                state["td_temps"][0], state["td_temps"][1],
                state["td_temps"][2], state["td_temps"][3],
                state["td_temps"][4], state["td_temps"][5],
                state["td_temps"][6], state["td_temps"][7],
                state["pantograph_up"],
                round(state["regen_energy"], 3),
                # DIESEL — None
                None, None, None, None, None, None, None, None,
                None, None, None, None,
            )
        else:
            row = (
                loco_id, ts,
                round(state["speed"], 1),
                state["brake"],
                state["battery"],
                km_pos,
                state["traction_mode"],
                state["error_code"],
                is_burst,
                # ELECTRIC — None
                None, None, None, None, None, None,
                None, None, None, None, None, None, None, None,
                None, None, None, None, None, None, None, None,
                None, None,
                # DIESEL
                round(state["fuel"], 1),
                state["fuel_consumption"],
                state["engine_rpm"],
                state["oil_temp"],
                state["coolant_temp"],
                state["oil_pressure"],
                state["traction_force"],
                state["main_gen_v"],
                state["axle_loads"][0], state["axle_loads"][1],
                state["axle_loads"][2], state["axle_loads"][3],
            )

        rows.append(row)

        # Collect events on threshold crossings
        ec = state.get("error_code")
        if ec and (step == 0 or ec != rows[-2][7] if len(rows) >= 2 else False):
            event_counter += 1
            severity = "CRITICAL" if ec in ("E001", "E011", "E012", "E022", "E041", "E042", "E051", "E052") else "WARN"
            events.append({
                "id": f"evt-{loco_id}-{event_counter:03d}",
                "loco_id": loco_id,
                "ts": ts,
                "severity": severity,
                "category": _error_category(ec),
                "title": _error_title(ec),
                "description": _error_description(ec, state, loco_type),
                "parameter_key": _error_param_key(ec),
                "parameter_value": _error_param_value(ec, state),
                "threshold": _error_threshold(ec),
                "auto_generated": True,
                "acknowledged": False,
                "recommended_action": _error_action(ec),
            })

    return rows, state, events


def _error_category(code: str) -> str:
    mapping = {
        "E001": "SYSTEM", "E011": "TEMPERATURE", "E012": "PRESSURE",
        "E013": "TEMPERATURE", "E014": "FUEL", "E021": "VOLTAGE",
        "E022": "VOLTAGE", "E041": "TEMPERATURE", "E042": "SYSTEM",
        "E051": "BRAKE", "E052": "BRAKE",
    }
    return mapping.get(code, "SYSTEM")


def _error_title(code: str) -> str:
    mapping = {
        "E001": "Общий системный сбой",
        "E011": "Перегрев масла двигателя",
        "E012": "Давление масла низкое",
        "E013": "Перегрев охлаждающей жидкости",
        "E014": "Топливо критически низкое",
        "E021": "Низкое напряжение контактной сети",
        "E022": "Перегрузка по току пантографа",
        "E041": "Перегрев тягового трансформатора",
        "E042": "Отказ тягового двигателя",
        "E051": "Давление тормозов вне диапазона",
        "E052": "Отказ ЭПТ",
    }
    return mapping.get(code, "Неизвестная ошибка")


def _error_description(code: str, state: dict, loco_type: str) -> str:
    if code == "E041":
        return f"Температура трансформатора {state.get('transformer_temp', 0):.1f}°C превысила порог 90°C"
    if code == "E011":
        return f"Температура масла {state.get('oil_temp', 0):.1f}°C превысила порог 90°C"
    if code == "E021":
        return f"Напряжение КС {state.get('catenary_v', 0):.1f} кВ ниже порога 23 кВ"
    return f"Код ошибки {code} зафиксирован системой диагностики"


def _error_param_key(code: str) -> str:
    mapping = {
        "E011": "oil_temp_c", "E041": "transformer_temp_c",
        "E021": "catenary_voltage_kv", "E022": "pantograph_current_a",
        "E051": "brake_pressure_atm", "E012": "oil_pressure_bar",
    }
    return mapping.get(code, "error_code")


def _error_param_value(code: str, state: dict) -> float:
    mapping = {
        "E011": state.get("oil_temp", 0),
        "E041": state.get("transformer_temp", 0),
        "E021": state.get("catenary_v", 0),
        "E022": state.get("pantograph_current", 0),
        "E051": state.get("brake", 0),
        "E012": state.get("oil_pressure", 0),
    }
    return float(mapping.get(code, 0))


def _error_threshold(code: str) -> float:
    mapping = {
        "E011": 90.0, "E041": 90.0, "E021": 23.0,
        "E022": 900.0, "E051": 6.5, "E012": 2.5,
    }
    return mapping.get(code, 0.0)


def _error_action(code: str) -> str:
    mapping = {
        "E011": "Снизить нагрузку, проверить систему смазки",
        "E041": "Снизить нагрузку до позиции П-7, проверить охлаждение трансформатора",
        "E021": "Снизить потребляемую мощность, сообщить диспетчеру",
        "E022": "Немедленно снизить тягу, проверить пантограф",
        "E051": "Остановить локомотив, проверить тормозную систему",
        "E012": "Остановить локомотив, проверить масляный насос",
    }
    return mapping.get(code, "Обратиться в техническую службу")


# ---------------------------------------------------------------------------
# Bulk insert helpers
# ---------------------------------------------------------------------------

TELEMETRY_INSERT_SQL = """
    INSERT INTO telemetry_readings (
        loco_id, ts, speed_kmh, brake_pressure_atm, battery_v,
        km_position, traction_mode, error_code, is_burst,
        catenary_voltage_kv, pantograph_current_a, power_consumption_kw,
        regen_power_kw, power_factor, transformer_temp_c,
        td1_current_a, td2_current_a, td3_current_a, td4_current_a,
        td5_current_a, td6_current_a, td7_current_a, td8_current_a,
        td1_temp_c, td2_temp_c, td3_temp_c, td4_temp_c,
        td5_temp_c, td6_temp_c, td7_temp_c, td8_temp_c,
        pantograph_up, regen_energy_kwh,
        fuel_level_liters, fuel_consumption_lh, engine_rpm,
        oil_temp_c, coolant_temp_c, oil_pressure_bar,
        traction_force_kn, main_gen_voltage_v,
        axle1_load_t, axle2_load_t, axle3_load_t, axle4_load_t
    ) VALUES %s
"""


def build_fleet() -> list[dict]:
    fleet = []
    driver_idx = 0
    loco_numbers: set[str] = set()
    scenario_idx = 0

    for series, prefix, loco_type, count, route_id in FLEET_SPEC:
        for _ in range(count):
            while True:
                num = str(random.randint(100, 999))
                loco_id = f"{prefix}-{num}"
                if loco_id not in loco_numbers:
                    loco_numbers.add(loco_id)
                    break

            scenario = SCENARIO_POOL[scenario_idx % len(SCENARIO_POOL)]
            # VOLTAGE_SAG only makes sense for ELECTRIC
            if scenario == "VOLTAGE_SAG" and loco_type == "DIESEL":
                scenario = "OVERHEAT"
            scenario_idx += 1

            fleet.append({
                "id": loco_id,
                "series": series,
                "number": num,
                "type": loco_type,
                "driver": DRIVERS[driver_idx % len(DRIVERS)],
                "status": "IN_MOTION",
                "route_id": route_id,
                "health_index": 100.0,
                "health_grade": "A",
                "scenario": scenario,
            })
            driver_idx += 1

    return fleet


# ---------------------------------------------------------------------------
# Main seeder
# ---------------------------------------------------------------------------

def main() -> None:
    print("Connecting to database...")
    conn = psycopg2.connect(DSN)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # 1. Routes
        print("Inserting routes...")
        psycopg2.extras.execute_values(
            cur,
            """INSERT INTO routes
               (id, from_station, to_station, total_km, electrified,
                schedule_departure, schedule_arrival)
               VALUES %s ON CONFLICT DO NOTHING""",
            [
                (r["id"], r["from_station"], r["to_station"], r["total_km"],
                 r["electrified"], r["schedule_departure"], r["schedule_arrival"])
                for r in ROUTES
            ],
        )

        # 2. Waypoints
        print("Inserting waypoints...")
        psycopg2.extras.execute_values(
            cur,
            """INSERT INTO route_waypoints
               (route_id, name, km_mark, lat, lon, speed_limit_kmh)
               VALUES %s ON CONFLICT DO NOTHING""",
            [
                (w["route_id"], w["name"], w["km_mark"],
                 w["lat"], w["lon"], w["speed_limit_kmh"])
                for w in WAYPOINTS
            ],
        )

        # 3. Locomotives (placeholder health)
        fleet = build_fleet()
        print(f"Inserting {len(fleet)} locomotives...")
        psycopg2.extras.execute_values(
            cur,
            """INSERT INTO locomotives
               (id, series, number, type, driver, status, route_id,
                health_index, health_grade)
               VALUES %s ON CONFLICT DO NOTHING""",
            [
                (l["id"], l["series"], l["number"], l["type"], l["driver"],
                 l["status"], l["route_id"], l["health_index"], l["health_grade"])
                for l in fleet
            ],
        )
        conn.commit()

        # 4. Telemetry + events per locomotive
        all_events: list[dict] = []
        health_updates: list[tuple] = []

        for i, loco in enumerate(fleet):
            print(
                f"  [{i+1}/{len(fleet)}] {loco['id']} "
                f"({loco['type']}, scenario={loco['scenario']})...",
                end=" ",
                flush=True,
            )
            rows, final_state, events = generate_telemetry(
                loco["id"], loco["type"], loco["scenario"]
            )

            # Compute health from last reading
            last_reading = {
                "traction_mode": rows[-1][6],
                "error_code": rows[-1][7],
                "brake_pressure_atm": rows[-1][3],
            }
            if loco["type"] == "ELECTRIC":
                last_reading.update({
                    "catenary_voltage_kv": rows[-1][9],
                    "transformer_temp_c": rows[-1][14],
                    **{f"td{j+1}_current_a": rows[-1][15 + j] for j in range(8)},
                })
            else:
                last_reading.update({
                    "oil_temp_c": rows[-1][33],
                    "fuel_level_liters": rows[-1][32],
                    **{f"td{j+1}_current_a": 0 for j in range(8)},
                })
            health_index, health_grade = calculate_health_index(last_reading, loco["type"])
            health_updates.append((health_index, health_grade, loco["id"]))

            psycopg2.extras.execute_values(
                cur, TELEMETRY_INSERT_SQL, rows, page_size=1000
            )
            conn.commit()
            all_events.extend(events)
            print(f"{len(rows)} rows, health={health_index} ({health_grade})")

        # 5. Update health
        print("Updating health indexes...")
        cur.executemany(
            "UPDATE locomotives SET health_index=%s, health_grade=%s WHERE id=%s",
            health_updates,
        )

        # 6. Pad events to meet distribution targets (min 50, 60% INFO)
        print("Inserting events...")
        # Add INFO events (W001 planned maintenance) if needed
        info_needed = max(0, int(len(all_events) * 0.6) - sum(1 for e in all_events if e["severity"] == "INFO"))
        for j, loco in enumerate(fleet[:info_needed]):
            evt_id = f"evt-{loco['id']}-w001"
            all_events.append({
                "id": evt_id,
                "loco_id": loco["id"],
                "ts": BASE_TS + timedelta(minutes=random.randint(5, 55)),
                "severity": "INFO",
                "category": "SYSTEM",
                "title": "Плановое ТО скоро",
                "description": "До планового технического обслуживания осталось менее 100 моточасов",
                "parameter_key": "engine_hours",
                "parameter_value": float(random.randint(8850, 8999)),
                "threshold": 9000.0,
                "auto_generated": True,
                "acknowledged": False,
                "recommended_action": "Запланировать ТО в ближайшем депо",
            })

        # Ensure at least 50 events total
        while len(all_events) < 50:
            loco = random.choice(fleet)
            evt_num = len(all_events) + 1
            all_events.append({
                "id": f"evt-filler-{evt_num:03d}",
                "loco_id": loco["id"],
                "ts": BASE_TS + timedelta(minutes=random.randint(1, 59)),
                "severity": "INFO",
                "category": "SYSTEM",
                "title": "Штатная диагностика",
                "description": "Результат автоматической самодиагностики — норма",
                "parameter_key": "system_status",
                "parameter_value": 0.0,
                "threshold": 0.0,
                "auto_generated": True,
                "acknowledged": False,
                "recommended_action": None,
            })

        psycopg2.extras.execute_values(
            cur,
            """INSERT INTO events
               (id, loco_id, ts, severity, category, title, description,
                parameter_key, parameter_value, threshold,
                auto_generated, acknowledged, recommended_action)
               VALUES %s ON CONFLICT DO NOTHING""",
            [
                (e["id"], e["loco_id"], e["ts"], e["severity"], e["category"],
                 e["title"], e["description"], e["parameter_key"],
                 e["parameter_value"], e["threshold"],
                 e["auto_generated"], e["acknowledged"], e["recommended_action"])
                for e in all_events
            ],
        )

        conn.commit()

        # Summary
        cur.execute("SELECT COUNT(*) FROM locomotives")
        loco_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM telemetry_readings")
        telemetry_count = cur.fetchone()[0]
        cur.execute("SELECT severity, COUNT(*) FROM events GROUP BY severity ORDER BY severity")
        event_stats = cur.fetchall()

        print("\n--- Seed complete ---")
        print(f"Locomotives:        {loco_count}")
        print(f"Telemetry readings: {telemetry_count:,}")
        print("Events by severity:")
        for severity, count in event_stats:
            print(f"  {severity}: {count}")

    except Exception as exc:
        conn.rollback()
        print(f"\nERROR: {exc}", file=sys.stderr)
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
