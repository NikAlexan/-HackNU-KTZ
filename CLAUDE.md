# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Virtual digital twin of a locomotive fleet (КТЖ / Kazakhstan Temir Zholy). Simulates two locomotive types — KZ8A (electric) and TE33A (diesel) — with real-time telemetry, component health tracking, and a dispatcher dashboard.

## Running the System

### Prerequisites
```bash
docker network create loco_shared
```

### Start everything (recommended)
```bash
make run
```

### Start individual services
```bash
cd LocoDashboardBack && docker compose up -d --build   # MQTT broker + API (:9000)
cd LocoAppBack && docker compose up -d --build         # 4 locomotive simulators (:8000–8003)
cd LocoDashboard && docker compose up -d --build       # Fleet UI (:3000)
cd LocoPanel && docker compose up -d --build           # Driver/dispatcher panels
```

### Stop everything
```bash
make stop
```

## Incident / Maintenance API

```bash
# Trigger incident on all 4 locomotives
make incident SCENARIO=OVERHEAT   # or CRITICAL_ALERT, VOLTAGE_SAG

# Clear forced scenario
make clear-incident

# Trigger on a single locomotive (API key required)
curl -X POST http://localhost:8000/api/maintenance/incident \
  -H "X-API-Key: super-secret-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{"scenario": "OVERHEAT"}'

# Repair components
curl -X POST http://localhost:8000/api/maintenance/repair \
  -H "X-API-Key: super-secret-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{"components": ["engine", "cooling_system"]}'
```

## Architecture

```
LocoAppBack (x4, :8000–8003)    LocoDashboardBack (:9000)    LocoDashboard (:3000)
┌────────────────────┐          ┌──────────────────┐         ┌─────────────┐
│  BCK-3 Simulator   │──MQTT───▶│  MQTT Subscriber │──WS────▶│  Fleet UI   │
│  WebSocket /ws     │◀──WS─────│  REST API        │◀────────│  Loco UI    │
└────────┬───────────┘          └──────┬───────────┘         └─────────────┘
         │                             │
    PostgreSQL                    PostgreSQL
 (locomotive_telemetry)          (loco_dashboard)
```

**LocoAppBack** — one container per locomotive. Runs the physics simulation, computes component health, streams telemetry over WebSocket (`/ws`) and MQTT (`loco/{id}/telemetry`).

**LocoDashboardBack** — server-side aggregator. Subscribes to MQTT, aggregates snapshots every 60 s, stores history in PostgreSQL, exposes REST + WebSocket proxy.

**LocoDashboard** — vanilla JS SPA. `fleet.html` (fleet overview) and `loco.html` (per-locomotive detail). Login: `admin` / `admin123`.

**LocoPanel** — Node.js server for standalone driver/dispatcher dashboards (connects via `/local/data` WebSocket).

## LocoAppBack — Key Files

| File | Purpose |
|------|---------|
| `app/generator.py` | Main simulation loop: simulate → extract sensors → update health → publish WS/MQTT |
| `app/telemetry/simulation.py` | Physics model: EMA-smoothed speed, scenario state machine |
| `app/telemetry/health.py` | `ComponentHealthTracker`, `calc_health_from_config` — monotonically decreasing health |
| `app/telemetry/risk.py` | `compute_risk` / `compute_component_risk`, sensor threshold configs |
| `app/telemetry/sensors_extract.py` | Extracts flat sensor dict from raw simulation state (branch per loco type) |
| `app/telemetry/node_config/kz8a_electro.yaml` | Component weights, damage rates, sensor thresholds for KZ8A |
| `app/telemetry/node_config/te33a_diesel.yaml` | Same for TE33A |
| `app/routers/maintenance.py` | `/api/maintenance/repair`, `/incident`, `/health` endpoints |

## LocoDashboardBack — Key Files

| File | Purpose |
|------|---------|
| `app/mqtt_subscriber.py` | MQTT listener, 60 s aggregation window, DB writes |
| `app/live_state.py` | In-memory last packet + accumulator for aggregation |
| `app/routers/auth.py` | JWT login (`/auth/login`), `/auth/me` |
| `app/routers/locomotives.py` | `/api/locomotives`, `/api/locomotives/{id}`, `/api/locomotives/register` |
| `app/routers/ingest.py` | `/api/ingest` — health snapshot from BCK-3 |
| `app/routers/ws.py` | WebSocket proxy: forwards BCK-3 stream to dashboard clients |

## Adding a New Locomotive Type

1. Create `LocoAppBack/app/telemetry/node_config/{series}_{type}.yaml`
2. Add sensor extraction branch in `app/telemetry/sensors_extract.py`
3. Add `init_state` / `evolve_state` branches in `app/telemetry/simulation.py`
4. Add a new service in `LocoAppBack/docker-compose.yml` with `LOCO_TYPE`, `LOCO_SERIES`, `LOCO_NODE_CONFIG` env vars

## Health Model

Component health is monotonically decreasing (0–100). Each tick:
```
health[comp] -= risk * damage_rate * dt_sec
```
`component_risks` (instantaneous, fluctuating) drive visual risk indicators only. `health_index` is the weighted average of all component healths.

## Environment Variables

**LocoAppBack**: `LOCO_ID`, `LOCO_TYPE`, `LOCO_SERIES`, `LOCO_NODE_CONFIG`, `DATABASE_URL`, `DASHBOARD_URL`, `REPORTER_API_KEY`, `MQTT_URL`

**LocoDashboardBack**: `DATABASE_URL`, `API_KEY`, `JWT_SECRET`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `MQTT_URL`
