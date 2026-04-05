"""
Risk calculation — pure functions.

Computes risk level [0.0, 1.0] for a single component given a flat sensors dict
and the component's config from the YAML node config file.

Supported risk_type values:
  linear_hi    — risk grows linearly above warn up to 1.0 at crit
  linear_lo    — risk grows linearly below warn down to 1.0 at crit
  ratio_hi     — compares value to a norm (%), risk from warn_pct to crit_pct
  band_outside — risk outside [ok_lo, ok_hi], max at [crit_lo, crit_hi]

Optional field in component config:
  exponent: float (default 1.0) — shapes the risk curve:
    1.0 → linear
    2.0 → slow near warn, steep near crit (quadratic)
    3.0+ → only severe deviations cause real damage
"""
import logging

logger = logging.getLogger(__name__)


def _curve(normalized: float, exponent: float) -> float:
    """Apply power-law curve to a normalized [0, 1] value."""
    return normalized ** exponent


def compute_risk(comp_cfg: dict, sensors: dict, norms: dict) -> float:
    """
    Return risk level in [0.0, 1.0] for a single component.

    Args:
        comp_cfg: Component config dict from YAML (risk_type, thresholds, exponent)
        sensors:  Flat sensor readings dict from extract_sensors()
        norms:    Norms dict from top-level YAML (reference values for ratio_hi)
    """
    state_key: str = comp_cfg["state_key"]
    value = sensors.get(state_key)
    if value is None:
        return 0.0

    risk_type: str = comp_cfg["risk_type"]
    exponent: float = float(comp_cfg.get("exponent", 1.0))

    if risk_type == "linear_hi":
        warn: float = comp_cfg["warn"]
        crit: float = comp_cfg["crit"]
        if value <= warn:
            return 0.0
        if value >= crit:
            return 1.0
        return _curve((value - warn) / (crit - warn), exponent)

    elif risk_type == "linear_lo":
        warn = comp_cfg["warn"]
        crit = comp_cfg["crit"]
        if value >= warn:
            return 0.0
        if value <= crit:
            return 1.0
        return _curve((warn - value) / (warn - crit), exponent)

    elif risk_type == "ratio_hi":
        norm_key: str = comp_cfg["norm_key"]
        nominal = norms.get(norm_key)
        if not nominal:
            return 0.0
        warn_pct: float = comp_cfg["warn_pct"]
        crit_pct: float = comp_cfg["crit_pct"]
        pct = (value / nominal) * 100.0
        if pct <= warn_pct:
            return 0.0
        if pct >= crit_pct:
            return 1.0
        return _curve((pct - warn_pct) / (crit_pct - warn_pct), exponent)

    elif risk_type == "band_outside":
        ok_lo: float = comp_cfg["ok_lo"]
        ok_hi: float = comp_cfg["ok_hi"]
        crit_lo: float = comp_cfg["crit_lo"]
        crit_hi: float = comp_cfg["crit_hi"]
        if ok_lo <= value <= ok_hi:
            return 0.0
        if value < ok_lo:
            if value <= crit_lo:
                return 1.0
            return _curve((ok_lo - value) / (ok_lo - crit_lo), exponent)
        # value > ok_hi
        if value >= crit_hi:
            return 1.0
        return _curve((value - ok_hi) / (crit_hi - ok_hi), exponent)

    logger.warning("Unknown risk_type %r for component — returning 0", risk_type)
    return 0.0
