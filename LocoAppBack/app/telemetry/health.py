"""
Health calculation and cumulative component health tracking.

Two responsibilities:
1. calc_health_from_config() — instantaneous health score derived from sensor risks.
   Config-driven replacement for the hardcoded calculate_health_index() in simulation.py.

2. ComponentHealthTracker — persistent cumulative health state per component node.
   Loaded from / flushed to the component_health DB table.
   Accepts a flat sensors dict — no knowledge of simulation internals.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ComponentHealth
from app.telemetry.risk import compute_risk

logger = logging.getLogger(__name__)

FLUSH_EVERY = 20  # ticks — flush to DB every 10 seconds (at 500 ms interval)


# ---------------------------------------------------------------------------
# Instantaneous health index
# ---------------------------------------------------------------------------

def calc_health_from_config(sensors: dict, node_cfg: dict) -> tuple[float, str]:
    """
    Compute instantaneous health score [0, 100] from current sensor readings.

    Score = 100 − mean(risk_per_component) × 100

    Each component is weighted equally; the exponent in each component's config
    already shapes how aggressively risk grows with deviation.

    Args:
        sensors:   Flat sensor readings from extract_sensors()
        node_cfg:  Loaded YAML node config dict

    Returns:
        (health_index: float, health_grade: str)
    """
    components: dict = node_cfg.get("components", {})
    norms: dict = node_cfg.get("norms", {})
    if not components:
        return 100.0, "A"

    risks = [compute_risk(cfg, sensors, norms) for cfg in components.values()]
    avg_risk = sum(risks) / len(risks)
    index = round(max(0.0, min(100.0, 100.0 - avg_risk * 100.0)), 1)

    if index >= 90:
        grade = "A"
    elif index >= 75:
        grade = "B"
    elif index >= 60:
        grade = "C"
    elif index >= 40:
        grade = "D"
    else:
        grade = "E"

    return index, grade


# ---------------------------------------------------------------------------
# Cumulative component health tracker
# ---------------------------------------------------------------------------

class ComponentHealthTracker:
    """
    In-memory health state loaded from / flushed to the component_health table.

    Accepts a flat sensors dict — knows nothing about simulation state structure.

    Usage:
        tracker = await ComponentHealthTracker.load(session, loco_id, node_cfg)
        ...
        snap = tracker.tick(sensors, dt_sec=0.5)
        if step % FLUSH_EVERY == 0:
            await tracker.flush(session)
    """

    def __init__(self, loco_id: str, node_cfg: dict) -> None:
        self.loco_id = loco_id
        self._components: dict[str, dict] = node_cfg.get("components", {})
        self._norms: dict = node_cfg.get("norms", {})
        self._damage_rate: float = node_cfg.get("damage_rate", 0.00347)

        self.health: dict[str, float] = {c: 100.0 for c in self._components}
        self.risk_accum: dict[str, float] = {c: 0.0 for c in self._components}

    @classmethod
    async def load(
        cls,
        session: AsyncSession,
        loco_id: str,
        node_cfg: dict,
    ) -> "ComponentHealthTracker":
        """Load state from DB. Components missing in DB start at health=100."""
        tracker = cls(loco_id, node_cfg)
        result = await session.execute(
            select(ComponentHealth).where(ComponentHealth.loco_id == loco_id)
        )
        for row in result.scalars().all():
            if row.component in tracker.health:
                tracker.health[row.component] = row.health
                tracker.risk_accum[row.component] = row.risk_accum
        logger.info(
            "Loaded component health for %s: %s",
            loco_id,
            {k: round(v, 1) for k, v in tracker.health.items()},
        )
        return tracker

    def tick(self, sensors: dict, dt_sec: float) -> dict[str, float]:
        """
        Apply damage based on current sensor readings.
        Returns snapshot {component: health} rounded to 1 decimal.
        """
        for comp, comp_cfg in self._components.items():
            risk = compute_risk(comp_cfg, sensors, self._norms)
            self.health[comp] = max(0.0, self.health[comp] - risk * self._damage_rate * dt_sec)
            self.risk_accum[comp] += risk * dt_sec
        return {c: round(v, 1) for c, v in self.health.items()}

    def current_risks(self, sensors: dict) -> dict[str, float]:
        """Return current risk level per component (0–1), for display."""
        return {
            comp: round(compute_risk(cfg, sensors, self._norms), 3)
            for comp, cfg in self._components.items()
        }

    async def repair(
        self,
        session: AsyncSession,
        components: list[str],
    ) -> list[str]:
        """Reset health=100 for specified components. Persists immediately."""
        repaired = []
        now = datetime.now(tz=timezone.utc)
        for comp in components:
            if comp not in self.health:
                logger.warning("Repair requested for unknown component %r — skipped", comp)
                continue
            self.health[comp] = 100.0
            self.risk_accum[comp] = 0.0
            repaired.append(comp)
            await session.execute(
                pg_insert(ComponentHealth)
                .values(
                    loco_id=self.loco_id, component=comp,
                    health=100.0, risk_accum=0.0,
                    last_repair=now, updated_at=now,
                )
                .on_conflict_do_update(
                    index_elements=["loco_id", "component"],
                    set_={"health": 100.0, "risk_accum": 0.0,
                          "last_repair": now, "updated_at": now},
                )
            )
        await session.commit()
        logger.info("Repaired components for %s: %s", self.loco_id, repaired)
        return repaired

    async def flush(self, session: AsyncSession) -> None:
        """Upsert current health state to DB for all components."""
        now = datetime.now(tz=timezone.utc)
        for comp, health_val in self.health.items():
            await session.execute(
                pg_insert(ComponentHealth)
                .values(
                    loco_id=self.loco_id, component=comp,
                    health=health_val, risk_accum=self.risk_accum[comp],
                    last_repair=None, updated_at=now,
                )
                .on_conflict_do_update(
                    index_elements=["loco_id", "component"],
                    set_={"health": health_val,
                          "risk_accum": self.risk_accum[comp],
                          "updated_at": now},
                )
            )
        await session.commit()
