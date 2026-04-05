"""
Background reporter: every 60 seconds aggregates generated_readings
and POSTs the result to the dashboard app.

Aggregation is done in Python from sensors_json — fully dynamic,
no hardcoded column references for specific sensor types.
"""
import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select

import app.generator as generator
from app.database import AsyncSessionLocal
from app.models import GeneratedReading

logger = logging.getLogger(__name__)

_INTERVAL_SEC = 60


async def _build_aggregate(period_start: datetime, period_end: datetime) -> dict:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(
                GeneratedReading.loco_id,
                GeneratedReading.loco_type,
                GeneratedReading.speed_kmh,
                GeneratedReading.health_index,
                GeneratedReading.health_grade,
                GeneratedReading.error_code,
                GeneratedReading.sensors_json,
            ).where(
                GeneratedReading.ts >= period_start,
                GeneratedReading.ts < period_end,
            )
        )
        rows = result.all()

    if not rows:
        return {}

    # Group rows by loco
    by_loco: dict[str, list] = defaultdict(list)
    for row in rows:
        by_loco[row.loco_id].append(row)

    locomotives = []
    for loco_id, loco_rows in by_loco.items():
        loco_type = loco_rows[0].loco_type
        readings_count = len(loco_rows)

        # Fixed-column aggregations
        avg_speed = sum(r.speed_kmh for r in loco_rows) / readings_count
        avg_health = sum(r.health_index for r in loco_rows) / readings_count
        error_count = sum(1 for r in loco_rows if r.error_code)

        # Final health grade: take the grade of the last reading in the period
        final_grade = loco_rows[-1].health_grade

        # Dynamic sensor aggregation from sensors_json
        sensor_vals: dict[str, list[float]] = defaultdict(list)
        for row in loco_rows:
            for key, val in (row.sensors_json or {}).items():
                if isinstance(val, (int, float)):
                    sensor_vals[key].append(float(val))

        metrics_json: dict = {}
        for key, vals in sensor_vals.items():
            metrics_json[f"avg_{key}"] = round(sum(vals) / len(vals), 3)
            metrics_json[f"max_{key}"] = round(max(vals), 3)
            metrics_json[f"min_{key}"] = round(min(vals), 3)

        # Current component health snapshot from tracker
        comp_health = (
            {c: round(v, 1) for c, v in generator.tracker.health.items()}
            if generator.tracker is not None
            else None
        )

        # Current instantaneous risk per component (from latest WS packet)
        comp_risks = (
            generator.latest_packet.get("component_risks")
            if generator.latest_packet is not None
            else None
        )

        locomotives.append({
            "loco_id": loco_id,
            "loco_type": loco_type,
            "readings_count": readings_count,
            "avg_speed_kmh": round(avg_speed, 2),
            "avg_health_index": round(avg_health, 1),
            "final_health_grade": final_grade,
            "error_count": error_count,
            "component_health": comp_health,
            "component_risks": comp_risks,
            "metrics_json": metrics_json,
        })

    return {
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "locomotives": locomotives,
    }


async def run_reporter(dashboard_url: str, api_key: str, interval: int = _INTERVAL_SEC) -> None:
    logger.info("Reporter started — interval %ds, dashboard: %s", interval, dashboard_url)
    while True:
        await asyncio.sleep(interval)
        period_end = datetime.now(tz=timezone.utc)
        period_start = period_end - timedelta(seconds=interval)

        try:
            payload = await _build_aggregate(period_start, period_end)
            if not payload:
                logger.debug("No readings in last %ds, skipping report", interval)
                continue

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{dashboard_url}/api/telemetry/aggregate",
                    json=payload,
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                resp.raise_for_status()
                logger.info(
                    "Reported %d locos to dashboard (%s)",
                    len(payload["locomotives"]),
                    period_end.strftime("%H:%M:%S"),
                )
        except Exception as exc:
            logger.warning("Reporter failed: %s", exc)
