"""
One-time registration of this locomotive in LocoDashboard on startup.
"""
import logging

import httpx

from app.config import LOCO_ID, LOCO_SERIES, LOCO_TYPE, REPORTER_API_KEY

logger = logging.getLogger(__name__)


async def register_in_dashboard(dashboard_url: str) -> None:
    url = f"{dashboard_url}/api/locomotives/register"
    payload = {"loco_id": LOCO_ID, "loco_type": LOCO_TYPE, "loco_series": LOCO_SERIES}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {REPORTER_API_KEY}"},
            )
            resp.raise_for_status()
            logger.info("Registration result: %s", resp.json().get("status"))
    except Exception as exc:
        logger.warning("Registration failed: %s", exc)