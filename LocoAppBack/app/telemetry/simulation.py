"""
In-memory locomotive telemetry simulation.
Shared between the WebSocket onboard-computer stream and (optionally) tests.

seed.py keeps its own copies for determinism — do NOT import from here in seed.py.
"""
import random

INTERVAL_MS = 500
_TOTAL_STEPS = 7200  # 1 hour @ 500 ms — used only as default for evolve_state progress calc


# ---------------------------------------------------------------------------
# Health index
# ---------------------------------------------------------------------------

def calculate_health_index(reading: dict, loco_type: str) -> tuple[float, str]:
    penalties = 0.0

    temp = reading.get("oil_temp_c") or reading.get("transformer_temp_c") or 0.0
    if temp > 95:
        penalties += 25.0
    elif temp > 80:
        penalties += 25.0 * (temp - 80.0) / 15.0

    if loco_type == "electro":
        v = reading.get("catenary_voltage_kv") or 25.0
        if v < 20:
            penalties += 20.0
        elif v < 23:
            penalties += 20.0 * (23.0 - v) / 3.0

    td_currents = [reading.get(f"td{i}_current_a") or 0.0 for i in range(1, 9)]
    max_td = max(td_currents)
    if max_td > 650:
        penalties += 20.0
    elif max_td > 550:
        penalties += 20.0 * (max_td - 550.0) / 100.0

    bp = reading.get("brake_pressure_atm", 5.0) or 5.0
    if bp < 3.5 or bp > 6.5:
        penalties += 20.0
    elif bp < 4.5:
        penalties += 20.0 * (4.5 - bp) / 1.0
    elif bp > 6.0:
        penalties += 20.0 * (bp - 6.0) / 0.5

    if loco_type == "diesel":
        fuel = reading.get("fuel_level_liters") or 8000.0
        pct = fuel / 16000.0
        if pct < 0.20:
            penalties += 10.0
        elif pct < 0.40:
            penalties += 10.0 * (0.40 - pct) / 0.20

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
# State initialisation
# ---------------------------------------------------------------------------

def _gauss(mu: float, sigma: float) -> float:
    return random.gauss(mu, sigma)


def init_state(loco_type: str) -> dict:
    if loco_type == "electro":
        return {
            "speed": 0.0,
            "brake": 5.2,
            "battery": 110.0,
            "catenary_v": 25.0,
            "transformer_temp": 45.0,
            "td_currents": [350.0] * 8,
            "td_temps": [55.0] * 8,
            "td_currents_max": 350.0,
            "pantograph_up": True,
            "regen_energy": 0.0,
            "compressor_temp": 35.0,
            "brake_fill_rate": 0.0,
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
            "compressor_temp": 35.0,
            "brake_fill_rate": 0.0,
            "error_code": None,
        }


# ---------------------------------------------------------------------------
# State evolution
# ---------------------------------------------------------------------------

def evolve_state(
    state: dict,
    loco_type: str,
    scenario: str,
    step: int,
    total_steps: int = _TOTAL_STEPS,
) -> dict:
    s = state.copy()
    if loco_type == "electro":
        s["td_currents"] = list(state["td_currents"])
        s["td_temps"] = list(state["td_temps"])
        s["axle_loads"] = None
    else:
        s["axle_loads"] = list(state["axle_loads"])

    dt_min = INTERVAL_MS / 1000 / 60
    t_sec = step * INTERVAL_MS / 1000

    # Speed profile: two legs per cycle with a station stop in the middle
    # Cycle: [0..TOTAL] split into two equal legs
    # Each leg: 15% accel → 70% cruise → 15% brake → (between legs) 10% stop
    #
    # Leg phases (within half-cycle):
    #   0.00–0.15 : acceleration
    #   0.15–0.80 : cruise
    #   0.80–0.95 : braking
    #   0.95–1.00 : station stop  (shared as gap between legs in full cycle)
    #
    # Full cycle mapping (0..1):
    #   leg1 : 0.00 – 0.45  (45 % of cycle)
    #   stop1: 0.45 – 0.50  ( 5 % of cycle)
    #   leg2 : 0.50 – 0.95  (45 % of cycle)
    #   stop2: 0.95 – 1.00  ( 5 % of cycle)

    progress = (step % total_steps) / total_steps

    def _leg_speed(leg_p: float) -> tuple[float, str]:
        """Given progress within a leg [0,1], return (target_speed, traction_mode)."""
        if leg_p < 0.15:
            return 120.0 * (leg_p / 0.15), "TRACTION"
        elif leg_p < 0.80:
            return 120.0, "TRACTION"
        elif leg_p < 0.95:
            return 120.0 * (1.0 - (leg_p - 0.80) / 0.15), "BRAKE"
        else:
            return 0.0, "IDLE"

    if progress < 0.45:
        leg_p = progress / 0.45
        target_speed, traction_mode = _leg_speed(leg_p)
        km_position = int(leg_p * 60)
    elif progress < 0.50:
        target_speed, traction_mode = 0.0, "IDLE"
        km_position = 60
    elif progress < 0.95:
        leg_p = (progress - 0.50) / 0.45
        target_speed, traction_mode = _leg_speed(leg_p)
        km_position = 60 + int(leg_p * 60)
    else:
        target_speed, traction_mode = 0.0, "IDLE"
        km_position = 120

    s["speed"] = max(0.0, target_speed + _gauss(0, 1.5))

    # Brake pressure
    if traction_mode == "BRAKE":
        s["brake"] = min(6.2, state["brake"] + _gauss(0.05, 0.01))
    elif traction_mode == "IDLE":
        s["brake"] = min(6.0, state["brake"] + _gauss(0.02, 0.01))
    else:
        s["brake"] = max(4.6, state["brake"] + _gauss(-0.01, 0.01))
    s["brake"] = round(max(3.0, min(7.0, s["brake"])), 2)

    s["battery"] = round(109.0 + _gauss(0, 0.5), 1)

    if loco_type == "electro":
        catenary_v = 25.0 + _gauss(0, 0.15)
        if scenario == "VOLTAGE_SAG" and 900 <= t_sec <= 1080:
            drop = (t_sec - 900) / 180 * 2.5
            catenary_v = 25.0 - drop + _gauss(0, 0.05)
        s["catenary_v"] = round(max(18.0, min(29.0, catenary_v)), 2)

        speed_factor = s["speed"] / 120.0
        power_kw = speed_factor * 5520.0 + _gauss(0, 50)
        pantograph_current = power_kw / (s["catenary_v"] * 1.0) if s["catenary_v"] > 0 else 0
        s["pantograph_current"] = round(max(0.0, pantograph_current), 1)

        load_factor = s["pantograph_current"] / 500.0
        dT = (load_factor * 2.0 - 0.8) * dt_min
        if scenario == "OVERHEAT" and t_sec >= 1800:
            dT += 0.08
        new_temp = state["transformer_temp"] + dT + _gauss(0, 0.05)
        s["transformer_temp"] = round(max(35.0, min(120.0, new_temp)), 1)

        for i in range(8):
            base_i = 300 + speed_factor * 200 + _gauss(0, 10)
            s["td_currents"][i] = round(max(0.0, base_i), 1)
            dT_td = (s["td_currents"][i] / 450 * 1.5 - 0.6) * dt_min
            new_td_temp = state["td_temps"][i] + dT_td + _gauss(0, 0.05)
            s["td_temps"][i] = round(max(30.0, min(120.0, new_td_temp)), 1)

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

        s["error_code"] = None
        if scenario == "VOLTAGE_SAG" and s["catenary_v"] < 23.0:
            s["error_code"] = "E021"
        elif scenario == "OVERHEAT" and s["transformer_temp"] > 90:
            s["error_code"] = "E041"
        elif scenario == "CRITICAL_ALERT" and t_sec >= 2700:
            s["transformer_temp"] = min(110.0, s["transformer_temp"] + 0.5)
            s["error_code"] = "E041"

        s["traction_mode"] = traction_mode

    else:  # DIESEL
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

    # Derived scalar sensors (both types)
    dt_sec = INTERVAL_MS / 1000
    # brake_fill_rate: pressure DROP = compressor refilling reservoir (atm/sec)
    s["brake_fill_rate"] = round(max(0.0, (state["brake"] - s["brake"]) / dt_sec), 4)
    if loco_type == "electro":
        s["td_currents_max"] = round(max(s["td_currents"]), 1)

    # Compressor temperature (shared: electro + diesel)
    # Load model:
    #   BRAKE mode        → high load (air consumed, compressor must refill after)
    #   TRACTION/IDLE after pressure drop (brake > 5.5) → moderate load (refilling)
    #   Cruise at normal pressure → minimal load (maintenance)
    if traction_mode == "BRAKE":
        compressor_load = 0.85
    elif s["brake"] > 5.6:
        compressor_load = 0.55   # refilling reservoirs after braking
    else:
        compressor_load = 0.10   # idle / maintenance
    dT_comp = (compressor_load * 2.2 - 0.9) * dt_min + _gauss(0, 0.04)
    s["compressor_temp"] = round(
        max(28.0, min(130.0, state.get("compressor_temp", 35.0) + dT_comp)), 1
    )

    s["km_position"] = km_position
    return s
