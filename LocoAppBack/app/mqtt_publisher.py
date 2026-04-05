"""
MQTT publisher: sends latest_packet every INTERVAL_MS to loco/{id}/telemetry.
Also handles tracker.flush() every FLUSH_EVERY ticks (moved from generator).
Reconnects automatically on broker loss.
"""
import asyncio
import json
import logging

import aiomqtt

import app.generator as generator
from app.config import LOCO_ID, MQTT_URL
from app.database import AsyncSessionLocal
from app.telemetry.health import FLUSH_EVERY
from app.telemetry.simulation import INTERVAL_MS

logger = logging.getLogger(__name__)

_TOPIC = f"loco/{LOCO_ID}/telemetry"
_RETRY_SEC = 5


def _parse_mqtt_url(url: str) -> tuple[str, int]:
    """Return (hostname, port) from mqtt://host:port URL."""
    netloc = url.removeprefix("mqtt://")
    host, _, port = netloc.partition(":")
    return host, int(port) if port else 1883


async def run_mqtt_publisher() -> None:
    hostname, port = _parse_mqtt_url(MQTT_URL)
    logger.info("MQTT publisher starting — broker %s:%d, topic %s", hostname, port, _TOPIC)

    tick = 0
    dt = INTERVAL_MS / 1000

    while True:
        try:
            async with aiomqtt.Client(hostname, port=port) as client:
                logger.info("MQTT publisher connected")
                while True:
                    if generator.latest_packet is not None:
                        payload = json.dumps(generator.latest_packet, default=str)
                        await client.publish(_TOPIC, payload=payload, qos=0)

                        tick += 1
                        if tick % FLUSH_EVERY == 0 and generator.tracker is not None:
                            async with AsyncSessionLocal() as session:
                                await generator.tracker.flush(session)

                    await asyncio.sleep(dt)
        except aiomqtt.MqttError as exc:
            logger.warning("MQTT publisher lost connection: %s — retry in %ds", exc, _RETRY_SEC)
            await asyncio.sleep(_RETRY_SEC)
        except Exception as exc:
            logger.error("MQTT publisher unexpected error: %s — retry in %ds", exc, _RETRY_SEC)
            await asyncio.sleep(_RETRY_SEC)
