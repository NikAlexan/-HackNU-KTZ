"""
MQTT subscriber for LocoDashboardBack.

Subscribes to loco/+/telemetry.
Per-packet:
  - Updates live_state (latest packet per loco + accumulator)
  - Notifies per-loco WS clients immediately

Every 60 seconds (aggregate loop):
  - Flushes accumulator → writes TelemetryAggregate + updates Locomotive health
"""
import asyncio
import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import aiomqtt

from app.database import AsyncSessionLocal
from app.models import HealthGrade, Locomotive, LocoStatus, TelemetryAggregate
from app import live_state

logger = logging.getLogger(__name__)

_MQTT_URL = os.getenv("MQTT_URL", "mqtt://localhost:1883")
_TOPIC = "loco/+/telemetry"
_AGGREGATE_SEC = 60
_RETRY_SEC = 5


def _parse_mqtt_url(url: str) -> tuple[str, int]:
    """Return (hostname, port) from mqtt://host:port URL."""
    netloc = url.removeprefix("mqtt://")
    host, _, port = netloc.partition(":")
    return host, int(port) if port else 1883


def _compute_aggregate(loco_id: str, packets: list, period_start: datetime, period_end: datetime) -> dict:
    count = len(packets)
    avg_speed = sum(p.get("speed", 0) for p in packets) / count
    avg_health = sum(p.get("health_index", 100) for p in packets) / count
    final_grade = packets[-1].get("health_grade", "A")
    error_count = sum(1 for p in packets if p.get("error_code"))
    loco_type = packets[0].get("loco_type", "electro")

    sensor_vals: dict[str, list] = defaultdict(list)
    for p in packets:
        for k, v in (p.get("sensors") or {}).items():
            if isinstance(v, (int, float)):
                sensor_vals[k].append(float(v))

    metrics_json: dict = {}
    for k, vals in sensor_vals.items():
        metrics_json[f"avg_{k}"] = round(sum(vals) / len(vals), 3)
        metrics_json[f"max_{k}"] = round(max(vals), 3)
        metrics_json[f"min_{k}"] = round(min(vals), 3)

    risk_vals: dict[str, list] = defaultdict(list)
    for p in packets:
        for comp, risk in (p.get("component_risks") or {}).items():
            if isinstance(risk, (int, float)):
                risk_vals[comp].append(float(risk))
    comp_risks = {comp: round(sum(v) / len(v), 4) for comp, v in risk_vals.items()} or None

    max_temp_c = metrics_json.get("max_transformer_temp") or metrics_json.get("max_oil_temp") or 0.0

    return {
        "loco_id": loco_id,
        "loco_type": loco_type,
        "period_start": period_start,
        "period_end": period_end,
        "readings_count": count,
        "avg_speed_kmh": round(avg_speed, 2),
        "avg_health_index": round(avg_health, 1),
        "final_health_grade": final_grade,
        "error_count": error_count,
        "metrics_json": metrics_json,
        "max_temp_c": max_temp_c,
        "min_voltage_kv": metrics_json.get("min_catenary_v"),
        "component_health": packets[-1].get("component_health"),
        "component_risks": comp_risks,
    }


async def _write_aggregate(agg: dict) -> None:
    async with AsyncSessionLocal() as session:
        session.add(TelemetryAggregate(
            loco_id=agg["loco_id"],
            loco_type=agg["loco_type"],
            period_start=agg["period_start"],
            period_end=agg["period_end"],
            readings_count=agg["readings_count"],
            avg_speed_kmh=agg["avg_speed_kmh"],
            max_temp_c=agg["max_temp_c"],
            min_voltage_kv=agg["min_voltage_kv"],
            avg_health_index=agg["avg_health_index"],
            final_health_grade=agg["final_health_grade"],
            error_count=agg["error_count"],
            metrics_json=agg["metrics_json"],
        ))

        db_loco = await session.get(Locomotive, agg["loco_id"])
        if db_loco is not None:
            db_loco.status = LocoStatus.IN_MOTION if agg["avg_speed_kmh"] > 1.0 else LocoStatus.STOPPED
            db_loco.health_index = agg["avg_health_index"]
            db_loco.health_grade = HealthGrade(agg["final_health_grade"])
            if agg["component_health"] is not None:
                db_loco.component_health = agg["component_health"]
            if agg["component_risks"] is not None:
                db_loco.component_risks = agg["component_risks"]

        await session.commit()


async def _aggregate_loop() -> None:
    while True:
        await asyncio.sleep(_AGGREGATE_SEC)
        period_end = datetime.now(tz=timezone.utc)
        period_start = period_end - timedelta(seconds=_AGGREGATE_SEC)

        for loco_id in live_state.all_loco_ids():
            packets = live_state.flush_accumulator(loco_id)
            if not packets:
                continue
            try:
                agg = _compute_aggregate(loco_id, packets, period_start, period_end)
                await _write_aggregate(agg)
                logger.info("Aggregate written for %s (%d packets)", loco_id, len(packets))
            except Exception as exc:
                logger.warning("Aggregate write failed for %s: %s", loco_id, exc)


async def _notify_loco_clients(loco_id: str, message: str) -> None:
    clients = live_state.notify_clients(loco_id)
    if not clients:
        return
    dead = set()
    for ws in list(clients):
        try:
            await ws.send_text(message)
        except Exception:
            dead.add(ws)
    for ws in dead:
        live_state.remove_client(loco_id, ws)


async def run_mqtt_subscriber() -> None:
    hostname, port = _parse_mqtt_url(_MQTT_URL)
    logger.info("MQTT subscriber starting — broker %s:%d, topic %s", hostname, port, _TOPIC)

    asyncio.create_task(_aggregate_loop())

    while True:
        try:
            async with aiomqtt.Client(hostname, port=port) as client:
                logger.info("MQTT subscriber connected")
                await client.subscribe(_TOPIC)
                async for message in client.messages:
                    try:
                        packet = json.loads(message.payload)
                        live_state.push(packet)
                        loco_id = packet.get("loco_id")
                        if loco_id:
                            await _notify_loco_clients(loco_id, message.payload.decode())
                    except Exception as exc:
                        logger.debug("Bad MQTT message: %s", exc)
        except aiomqtt.MqttError as exc:
            logger.warning("MQTT subscriber lost connection: %s — retry in %ds", exc, _RETRY_SEC)
            await asyncio.sleep(_RETRY_SEC)
        except Exception as exc:
            logger.error("MQTT subscriber unexpected error: %s — retry in %ds", exc, _RETRY_SEC)
            await asyncio.sleep(_RETRY_SEC)
