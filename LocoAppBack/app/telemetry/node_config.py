"""
Node configuration loader.

Loads the YAML file that defines which components to monitor, their sensor keys,
risk thresholds, and damage rates. All risk calculation logic lives in risk.py.
"""
import logging
import os
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).parent / "node_config"
_DEFAULTS = {
    "electro": str(_CONFIG_DIR / "kz8a_electro.yaml"),
    "diesel": str(_CONFIG_DIR / "te33a_diesel.yaml"),
}


def load_node_config(path: str, loco_type: str) -> dict:
    """
    Load YAML node config. Falls back to built-in default for loco_type if path is empty.

    Args:
        path:      Absolute path to YAML file (from LOCO_NODE_CONFIG env var).
                   Pass empty string to use the built-in default for loco_type.
        loco_type: "electro" or "diesel" — used to select the default config.

    Returns:
        Parsed YAML dict with keys: damage_rate, norms, components.
    """
    resolved = path or _DEFAULTS.get(loco_type, "")
    if not resolved:
        raise RuntimeError(f"No node config path for loco_type={loco_type!r}")
    if not os.path.exists(resolved):
        raise FileNotFoundError(f"Node config not found: {resolved}")
    with open(resolved) as f:
        cfg = yaml.safe_load(f)
    logger.info(
        "Loaded node config from %s (%d components)",
        resolved,
        len(cfg.get("components", {})),
    )
    return cfg
