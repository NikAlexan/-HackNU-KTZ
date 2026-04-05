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
from app.config import LOCO_ID, LOCO_TYPE, REPORTER_API_KEY
from app.database import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _require_api_key(key: str | None = Security(_api_key_header)) -> str:
    if key != REPORTER_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return key


_VALID_SCENARIOS = {"NORMAL_RUN", "OVERHEAT", "CRITICAL_ALERT", "VOLTAGE_SAG"}


class RepairRequest(BaseModel):
    components: list[str]


class IncidentRequest(BaseModel):
    scenario: str  # OVERHEAT | CRITICAL_ALERT | VOLTAGE_SAG | NORMAL_RUN


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


@router.post("/incident")
async def set_incident(
    body: IncidentRequest,
    _: str = Depends(_require_api_key),
) -> dict:
    """Force a specific simulation scenario (e.g. OVERHEAT). Pass NORMAL_RUN to clear."""
    scenario = body.scenario.upper()
    allowed = _VALID_SCENARIOS if LOCO_TYPE == "electro" else _VALID_SCENARIOS - {"VOLTAGE_SAG"}
    if scenario not in allowed:
        raise HTTPException(status_code=422, detail=f"Unknown scenario. Allowed: {sorted(allowed)}")
    generator.active_scenario = None if scenario == "NORMAL_RUN" else scenario
    logger.info("Scenario overridden → %s", scenario)
    return {"loco_id": LOCO_ID, "active_scenario": scenario}


@router.delete("/incident")
async def clear_incident(_: str = Depends(_require_api_key)) -> dict:
    """Clear forced scenario — resume random simulation."""
    generator.active_scenario = None
    return {"loco_id": LOCO_ID, "active_scenario": None}


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
