"""
POST /api/maintenance/repair — reset health for specified locomotive components.

Protected by the same X-API-Key used for telemetry reporting.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

import app.generator as generator
from app.config import LOCO_ID, REPORTER_API_KEY
from app.database import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _require_api_key(key: str | None = Security(_api_key_header)) -> str:
    if key != REPORTER_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return key


class RepairRequest(BaseModel):
    components: list[str]


@router.post("/repair")
async def repair_components(
    body: RepairRequest,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(_require_api_key),
) -> dict:
    if generator.tracker is None:
        raise HTTPException(status_code=503, detail="Generator not ready yet")

    repaired = await generator.tracker.repair(session, body.components)

    return {
        "loco_id": LOCO_ID,
        "repaired": repaired,
        "health": {c: generator.tracker.health.get(c) for c in repaired},
    }


@router.get("/health")
async def get_component_health(
    _: str = Depends(_require_api_key),
) -> dict:
    """Return current component health snapshot."""
    if generator.tracker is None:
        raise HTTPException(status_code=503, detail="Generator not ready yet")
    return {
        "loco_id": LOCO_ID,
        "component_health": {c: round(v, 1) for c, v in generator.tracker.health.items()},
    }
