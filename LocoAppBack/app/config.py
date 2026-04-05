import os

LOCO_ID = os.environ["LOCO_ID"]
LOCO_TYPE = os.environ["LOCO_TYPE"]
LOCO_SERIES = os.getenv("LOCO_SERIES", "UNKNOWN")
REPORTER_API_KEY = os.environ["REPORTER_API_KEY"]
LOCO_NODE_CONFIG = os.getenv("LOCO_NODE_CONFIG", "")
MQTT_URL = os.getenv("MQTT_URL", "mqtt://localhost:1883")

if LOCO_TYPE not in ("electro", "diesel"):
    raise ValueError(f"LOCO_TYPE must be electro or diesel, got: {LOCO_TYPE!r}")
