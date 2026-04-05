"""
Cumulative component health tracker.

Keeps persistent health state per locomotive node. On each tick, damage is
applied based on the current risk level computed from telemetry. Health is
restored only via an explicit repair call (per component).

This module is fully decoupled from simulation.py — it knows nothing about
how state is generated; it only reads values from the state dict using keys
defined in the node config YAML.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ComponentHealth
from app.telemetry.node_config import compute_risk

logger = logging.getLogger(__name__)

FLUSH_EVERY = 20  # ticks — flush to DB every 10 seconds (at 500 ms interval)


class ComponentHealthTracker:
    """
    In-memory health state loaded from / flushed to the component_health table.

    Usage:
        tracker = await ComponentHealthTracker.load(session, loco_id, node_cfg)
        ...
        snap = tracker.tick(state, dt_sec=0.5)
        if step % FLUSH_EVERY == 0:
            await tracker.flush(session)
    """

    def __init__(self, loco_id: str, node_cfg: dict) -> None:
        self.loco_id = loco_id
        self._cfg = node_cfg
        self._components: dict[str, dict] = node_cfg.get("components", {})
        self._norms: dict = node_cfg.get("norms", {})
        self._damage_rate: float = node_cfg.get("damage_rate", 0.00347)

        # Mutable state
        self.health: dict[str, float] = {c: 100.0 for c in self._components}
        self.risk_accum: dict[str, float] = {c: 0.0 for c in self._components}

        # For derived metrics
        self._prev_brake: float | None = None

    @classmethod
    async def load(
        cls,
        session: AsyncSession,
        loco_id: str,
        node_cfg: dict,
    ) -> "ComponentHealthTracker":
        """Load from DB. Components missing in DB start at health=100."""
        tracker = cls(loco_id, node_cfg)
        result = await session.execute(
            select(ComponentHealth).where(ComponentHealth.loco_id == loco_id)
        )
        rows = result.scalars().all()
        for row in rows:
            if row.component in tracker.health:
                tracker.health[row.component] = row.health
                tracker.risk_accum[row.component] = row.risk_accum
        logger.info(
            "Loaded component health for %s: %s",
            loco_id,
            {k: round(v, 1) for k, v in tracker.health.items()},
        )
        return tracker

    def tick(self, state: dict, dt_sec: float) -> dict[str, float]:
        """
        Apply damage to all components based on current telemetry state.
        Returns a snapshot {component: health} with values rounded to 1 decimal.
        """
        # Inject derived metrics into a working copy of state so compute_risk stays pure
        effective_state = state.copy()

        # brake_fill_rate: rate at which brake reservoir is being refilled (atm/sec).
        # Positive delta = compressor actively filling; negative = air being consumed (braking).
        # Only positive rate (filling) stresses the compressor.
        current_brake = state.get("brake", 5.2)
        if self._prev_brake is not None and dt_sec > 0:
            effective_state["brake_fill_rate"] = max(
                0.0, (current_brake - self._prev_brake) / dt_sec
            )
        else:
            effective_state["brake_fill_rate"] = 0.0
        self._prev_brake = current_brake

        for comp, comp_cfg in self._components.items():
            risk = compute_risk(comp_cfg, effective_state, self._norms)
            damage = risk * self._damage_rate * dt_sec
            self.health[comp] = max(0.0, self.health[comp] - damage)
            self.risk_accum[comp] += risk * dt_sec

        return {c: round(v, 1) for c, v in self.health.items()}

    def current_risks(self, state: dict) -> dict[str, float]:
        """Return current risk level for each component (0–1), for display."""
        effective_state = state.copy()
        effective_state["brake_fill_rate"] = max(
            0.0,
            (state.get("brake", 5.2) - (self._prev_brake or state.get("brake", 5.2)))
            / 0.5,
        )
        return {
            comp: round(compute_risk(comp_cfg, effective_state, self._norms), 3)
            for comp, comp_cfg in self._components.items()
        }

    async def repair(
        self,
        session: AsyncSession,
        components: list[str],
    ) -> list[str]:
        """
        Reset health=100 and risk_accum=0 for the specified components.
        Immediately persists the repaired rows to DB.
        Returns list of actually repaired component names.
        """
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
                    loco_id=self.loco_id,
                    component=comp,
                    health=100.0,
                    risk_accum=0.0,
                    last_repair=now,
                    updated_at=now,
                )
                .on_conflict_do_update(
                    index_elements=["loco_id", "component"],
                    set_={
                        "health": 100.0,
                        "risk_accum": 0.0,
                        "last_repair": now,
                        "updated_at": now,
                    },
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
                    loco_id=self.loco_id,
                    component=comp,
                    health=health_val,
                    risk_accum=self.risk_accum[comp],
                    last_repair=None,
                    updated_at=now,
                )
                .on_conflict_do_update(
                    index_elements=["loco_id", "component"],
                    set_={
                        "health": health_val,
                        "risk_accum": self.risk_accum[comp],
                        "updated_at": now,
                    },
                )
            )
        await session.commit()
