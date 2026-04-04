"""
Background reporter: every 5 minutes aggregates generated_readings
and POSTs the result to the dashboard app.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import func, select

from app.database import AsyncSessionLocal
from app.models import GeneratedReading

logger = logging.getLogger(__name__)

_INTERVAL_SEC = 300  # 5 minutes


async def _build_aggregate(period_start: datetime, period_end: datetime) -> dict:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(
                GeneratedReading.loco_id,
                GeneratedReading.loco_type,
                func.count().label("readings_count"),
                func.avg(GeneratedReading.speed_kmh).label("avg_speed_kmh"),
                func.max(
                    func.coalesce(GeneratedReading.transformer_temp_c, GeneratedReading.oil_temp_c)
                ).label("max_temp_c"),
                func.min(GeneratedReading.catenary_voltage_kv).label("min_voltage_kv"),
                func.avg(GeneratedReading.health_index).label("avg_health_index"),
                func.count(GeneratedReading.error_code).label("error_count"),
            )
            .where(
                GeneratedReading.ts >= period_start,
                GeneratedReading.ts < period_end,
            )
            .group_by(GeneratedReading.loco_id, GeneratedReading.loco_type)
        )
        rows = result.all()

    if not rows:
        return {}

    # Final health grade: take the last reading per loco
    grades: dict[str, str] = {}
    async with AsyncSessionLocal() as session:
        for row in rows:
            latest = await session.execute(
                select(GeneratedReading.health_grade)
                .where(
                    GeneratedReading.loco_id == row.loco_id,
                    GeneratedReading.ts >= period_start,
                    GeneratedReading.ts < period_end,
                )
                .order_by(GeneratedReading.ts.desc())
                .limit(1)
            )
            grade_row = latest.scalar_one_or_none()
            grades[row.loco_id] = grade_row or "A"

    locomotives = []
    for row in rows:
        locomotives.append({
            "loco_id": row.loco_id,
            "loco_type": row.loco_type,
            "readings_count": row.readings_count,
            "avg_speed_kmh": round(row.avg_speed_kmh or 0.0, 2),
            "max_temp_c": round(row.max_temp_c or 0.0, 1),
            "min_voltage_kv": round(row.min_voltage_kv, 2) if row.min_voltage_kv is not None else None,
            "avg_health_index": round(row.avg_health_index or 0.0, 1),
            "final_health_grade": grades[row.loco_id],
            "error_count": row.error_count,
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
