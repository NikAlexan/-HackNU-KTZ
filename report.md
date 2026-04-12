# SRE Midterm Report

## Production-Ready Observability for a Custom Web Application

### Virtual Digital Twin of the KTZ Locomotive Fleet

**Student:** Nikita Vassilenko | SE-2410

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Application Architecture](#2-application-architecture)
3. [Step 1: Containerization (Docker)](#3-step-1-containerization-docker)
4. [Step 1 BONUS: Docker Swarm Deployment](#4-step-1-bonus-docker-swarm-deployment)
5. [Step 2: SLI, SLO, and Error Budget](#5-step-2-sli-slo-and-error-budget)
6. [Step 3: Monitoring and Dashboards (Grafana)](#6-step-3-monitoring-and-dashboards-grafana)
7. [Step 4: Alerting Validation (Prometheus)](#7-step-4-alerting-validation-prometheus)
8. [Post-Deployment Fixes](#8-post-deployment-fixes)
9. [Conclusion](#9-conclusion)

---

## 1. Project Overview

The application is a **virtual digital twin of a locomotive fleet** developed for Kazakhstan Temir Zholy (KTZ). It simulates the on-board telemetry computer (BCK-3) installed on two real locomotive series:

- **KZ8A** (Alstom Prima T8) — electric locomotive
- **TE33A** (GE Evolution Series) — diesel locomotive

The system solves real-world SRE challenges:

- Continuous real-time monitoring of component states
- Wear accumulation tracking against manufacturer thresholds
- Early deviation detection (overheating, voltage sag, turbocharger failure)
- Maintenance decision support

As Lead SRE, the goal is to take this application, deploy it in a production-grade manner using Docker Swarm, establish SLOs for the dispatcher infrastructure, and build a complete observability stack.

---

## 2. Application Architecture

```
LocoAppBack (×4, ports 8000–8003)      LocoDashboardBack (port 9000)     LocoDashboard (port 3000)
┌─────────────────────────┐            ┌──────────────────────────┐      ┌──────────────────┐
│  BCK-3 On-Board         │──MQTT────▶│  MQTT Subscriber          │─WS──▶│  Fleet UI        │
│  Simulator (FastAPI)    │            │  Aggregator (FastAPI)     │◀─────│  (Vanilla JS SPA)│
│  WebSocket /ws          │◀───WS──────│  REST API                │      └──────────────────┘
└────────────┬────────────┘            └───────────┬──────────────┘
             │                                      │
        PostgreSQL                            PostgreSQL
     (per-locomotive DB)                    (loco_dashboard)
```

**Component responsibilities:**

| Service | Role |
|---------|------|
| **LocoAppBack** | One container per locomotive. Runs physics simulation, computes component health, streams telemetry over WebSocket and MQTT. Designed for **unstable connectivity** — reconnects automatically. |
| **LocoDashboardBack** | Central server. Subscribes to MQTT, aggregates data every 60 s, stores history in PostgreSQL, exposes REST API and WebSocket proxy for the dashboard. **Stable, SLO-bearing service.** |
| **LocoDashboard** | Vanilla JS SPA. Fleet overview and per-locomotive detail pages. |
| **LocoPanel** | Standalone Node.js server for driver and dispatcher panels. |

**Key design insight for SRE:** The on-board computers (LocoAppBack) are explicitly designed for intermittent connectivity. They reconnect automatically when the central server is reachable. **SLOs are defined on LocoDashboardBack** (the stable dispatcher infrastructure), not on the locomotive boards themselves.

---

## 3. Step 1: Containerization (Docker)

### Dockerfiles

**LocoAppBack** (`LocoAppBack/Dockerfile`):

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh
CMD ["./entrypoint.sh"]
```

The entrypoint runs Alembic migrations before starting uvicorn:

```sh
#!/bin/sh
set -e
alembic upgrade head
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**LocoDashboardBack** (`LocoDashboardBack/Dockerfile`) — identical pattern, port 9000.

**LocoDashboard** (`LocoDashboard/Dockerfile`):

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
```

**LocoPanel** (`LocoPanel/Dockerfile`) — identical pattern, port 4000.

### Docker Compose (development)

The existing `docker-compose.yml` files are preserved unchanged for local development:

| File | Services |
|------|----------|
| `LocoDashboardBack/docker-compose.yml` | MQTT (EMQX), dashboard DB, dashboard API |
| `LocoAppBack/docker-compose.yml` | Shared app DB, 4 locomotive simulators |
| `LocoDashboard/docker-compose.yml` | Fleet UI |
| `LocoPanel/docker-compose.yml` | Driver/dispatcher panels |

Start with compose:

```bash
docker network create loco_shared
make run
```

---

## 4. Step 1 BONUS: Docker Swarm Deployment

### Architecture Decision: Three Separate Stacks

The application is split into three independent Swarm stacks, reflecting clear operational boundaries:

| Stack | File | Contains |
|-------|------|----------|
| `dashboard_stack` | `docker-stack-dashboard.yml` | MQTT, Dispatcher API + DB, Fleet UI, Panel UI |
| `loco_stack` | `docker-stack-loco.yml` | 4 locomotive simulators + 4 PostgreSQL DBs |
| `monitoring_stack` | `docker-stack-monitoring.yml` | Prometheus, Grafana, Node Exporter, Blackbox Exporter |

**Why separate stacks?** This split allows independent lifecycle management: UI/API changes, locomotive simulation changes, and observability changes can be rolled out independently without coupling failures across domains.

**Why a database per locomotive?** Each BCK-3 computer stores its own telemetry locally, independent of network availability. This mirrors the real architecture where a locomotive's on-board computer operates autonomously. In the Swarm stack, each locomotive service connects to its dedicated PostgreSQL instance:

```
loco_kz8a_001  →  db_kz8a_001  (DB: loco_kz8a_001)
loco_kz8a_002  →  db_kz8a_002  (DB: loco_kz8a_002)
loco_te33a_001 →  db_te33a_001 (DB: loco_te33a_001)
loco_te33a_002 →  db_te33a_002 (DB: loco_te33a_002)
```

### Shared Overlay Network

All stacks communicate via a single overlay network `loco_shared`:

```bash
docker network create --driver overlay --attachable loco_shared
```

All stack files declare it as `external: true`, so the network outlives any individual stack.

### Swarm-Specific Adaptations

| docker-compose feature | Swarm equivalent |
|------------------------|------------------|
| `build: .` | `image: loco_app_back:swarm` (pre-built) |
| `container_name:` | Removed — Swarm names containers automatically |
| `depends_on:` | Removed — `restart_policy: condition: on-failure, max_attempts: 10, delay: 5s` |
| `volumes: .:/app` | Removed — production image contains the code |
| `networks: [default, loco_shared]` | `networks: [loco_shared]` (single overlay) |

### Deployment Commands

```bash
# 1. Initialize Swarm on this node
make swarm-init

# 2. Build application images
make swarm-build

# 3. Deploy all stacks
make swarm-deploy

# 4. Check service status
make swarm-status

# 5. Tear down
make swarm-down
```

**Expected output of `make swarm-status` (abbreviated):**

```
=== Dashboard Stack (dashboard_stack) ===
...  dashboard_stack_mqtt              replicated  1/1
...  dashboard_stack_db_dashboard      replicated  1/1
...  dashboard_stack_dashboard_api     replicated  1/1
...  dashboard_stack_dashboard_ui      replicated  1/1
...  dashboard_stack_panel_ui          replicated  1/1

=== Loco Stack (loco_stack) ===
...            loco_stack_db_kz8a_001            replicated  1/1   postgres:16-alpine
...            loco_stack_db_kz8a_002            replicated  1/1   postgres:16-alpine
...            loco_stack_db_te33a_001           replicated  1/1   postgres:16-alpine
...            loco_stack_db_te33a_002           replicated  1/1   postgres:16-alpine
...            loco_stack_loco_kz8a_001          replicated  1/1   loco_app_back:swarm
...            loco_stack_loco_kz8a_002          replicated  1/1   loco_app_back:swarm
...            loco_stack_loco_te33a_001         replicated  1/1   loco_app_back:swarm
...            loco_stack_loco_te33a_002         replicated  1/1   loco_app_back:swarm

=== Monitoring Stack (monitoring_stack) ===
...  monitoring_stack_prometheus       replicated  1/1
...  monitoring_stack_grafana          replicated  1/1
...  monitoring_stack_node_exporter    global      1/1
...  monitoring_stack_blackbox         replicated  1/1
```

**Service URLs after deployment:**

| Service | URL |
|---------|-----|
| Fleet Dashboard | <http://127.0.0.1:3000/login.html> (admin / admin123) |
| Dispatcher API | <http://127.0.0.1:9000> |
| Prometheus | <http://127.0.0.1:9090> |
| Grafana | <http://127.0.0.1:3001> (admin / admin) |
| EMQX Console | <http://127.0.0.1:18083> |

---

## 5. Step 2: SLI, SLO, and Error Budget

### Monitoring Philosophy

The on-board computers (LocoAppBack) are designed for unstable communication — they reconnect automatically and do not contribute to service reliability SLOs. All SLOs are defined on **LocoDashboardBack**, the central dispatcher API that operators depend on.

Metrics are collected via `prometheus-fastapi-instrumentator` added to `LocoDashboardBack`. This library automatically instruments all HTTP endpoints and exposes a `/metrics` endpoint with:

- `http_requests_total{method, status, handler}` — counter
- `http_request_duration_seconds_bucket{method, handler, le}` — histogram

### SLI 1: Request Availability

**Definition:** The proportion of HTTP requests to LocoDashboardBack that return a non-5xx response.

```
SLI₁ = (total requests − 5xx responses) / total requests
     = sum(rate(http_requests_total{status!~"5.."}[5m]))
       ─────────────────────────────────────────────────
       sum(rate(http_requests_total[5m]))
```

**Rationale:** Dispatcher operators rely on the API for fleet monitoring, authentication, and maintenance actions. A 5xx error means the operator received no useful response — a genuine availability failure.

**SLO₁ = 99.5% of requests succeed over any 30-day rolling window.**

### SLI 2: Request Latency

**Definition:** The proportion of HTTP requests to LocoDashboardBack that complete in under 500 ms.

```
SLI₂ = requests completed in < 500 ms / total requests
     = sum(rate(http_request_duration_seconds_bucket{le="0.5"}[5m]))
       ────────────────────────────────────────────────────────────
       sum(rate(http_request_duration_seconds_count[5m]))
```

**Rationale:** Dispatchers monitor live telemetry for safety-critical decisions. A response taking more than 500 ms degrades the real-time nature of the system. The 500 ms threshold comes from Google's research that user perception of "instantaneous" response is under 100 ms, but for data-heavy API responses 500 ms is a reasonable operational target.

**SLO₂ = 99.0% of requests complete in under 500 ms over any 30-day rolling window.**

### Error Budget Calculations

A 30-day month contains:  
`30 days × 24 hours × 60 minutes = 43,200 minutes`

**Error Budget for SLO₁ (Availability, 99.5%):**

```
Allowed failure rate = 1 − 0.995 = 0.5%
Error budget         = 0.5% × 43,200 min = 216 minutes = 3 hours 36 minutes / month
```

**Error Budget for SLO₂ (Latency, 99.0%):**

```
Allowed failure rate = 1 − 0.990 = 1.0%
Error budget         = 1.0% × 43,200 min = 432 minutes = 7 hours 12 minutes / month
```

### Error Budget Interpretation

| Remaining Budget | Action |
|-----------------|--------|
| > 50% | Normal operations, new feature deployments allowed |
| 25–50% | Caution — review recent incidents, slow down risky deployments |
| 0–25% | Freeze non-essential changes, focus on reliability improvements |
| 0% (exhausted) | Incident response mode, all deployments blocked until next window |

---

## 6. Step 3: Monitoring and Dashboards (Grafana)

### Observability Stack

The observability stack runs in a dedicated `monitoring_stack` and consists of:

| Component | Purpose | Port |
|-----------|---------|------|
| **Prometheus** `v3.4.0` | Metrics collection and alerting | 9090 |
| **Grafana** `11.6.1` | Visualization and dashboards | 3001 |
| **Node Exporter** `v1.9.1` | Host CPU, memory, disk metrics | 9100 |
| **Blackbox Exporter** `v0.25.0` | HTTP endpoint availability probes | 9115 |

### Prometheus Targets

`prometheus/prometheus.yml` configures four scrape jobs:

| Job | Target | What it measures |
|-----|--------|-----------------|
| `loco_dashboard_api` | `dashboard_api:9000/metrics` | FastAPI request metrics (SLI 1 & 2) |
| `node_exporter` | `node_exporter:9100/metrics` | Host CPU, memory, filesystem |
| `blackbox_http` | `dashboard_api:9000/`, `dashboard_ui:3000/login.html` | Dispatcher infrastructure availability |
| `blackbox_loco_boards` | `loco_kz8a_001:8000/` … `loco_te33a_002:8000/` | On-board connectivity (informational only) |

The locomotive boards are probed but their downtime **does not** affect SLOs — this is by design.

### Grafana Dashboard: Golden Signals

The dashboard `grafana/dashboards/loco_digital_twin.json` is automatically provisioned and contains three row sections:

**Row 1 — Golden Signals (Dispatcher API)**

| Panel | Type | PromQL |
|-------|------|--------|
| Traffic (RPS) | Time series | `sum(rate(http_requests_total{job="loco_dashboard_api"}[1m]))` |
| Errors (5xx %) | Time series | `100 * sum(rate(...{status=~"5.."}[1m])) / sum(rate(...[1m]))` |
| Latency p50/p95/p99 | Time series | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))` |
| Saturation CPU/Memory | Time series | Node Exporter — CPU idle rate, memory available |

**Row 2 — SLO Compliance**

| Panel | Type | Threshold |
|-------|------|-----------|
| SLO 1: Availability | Stat (background color) | Green ≥ 99.5%, Yellow ≥ 99.0%, Red < 99.0% |
| SLO 2: Latency < 500ms | Stat (background color) | Green ≥ 99.0%, Yellow ≥ 98.0%, Red < 98.0% |
| Error Budget Availability | Stat | Shows burned seconds vs 216 min monthly budget |
| Error Budget Latency | Stat | Shows burned seconds vs 432 min monthly budget |

**Row 3 — Availability Probes**

| Panel | Shows |
|-------|-------|
| Dispatcher API & UI Probe | `probe_success` for `:9000` and `:3000` — UP/DOWN |
| On-Board Computers Probe | `probe_success` for all 4 BCK-3 boards — ONLINE/OFFLINE |

### Grafana Access

URL: <http://127.0.0.1:3001>  
Credentials: `admin` / `admin`  
The dashboard is auto-provisioned on startup — no manual import required.

---

## 7. Step 4: Alerting Validation (Prometheus)

### Alert Rules

Alert rules are defined in `prometheus/alert_rules.yml`:

#### Group: `loco_slo_alerts`

**Alert 1: `LocoAPIHighErrorRate` (severity: warning)**

```yaml
expr: |
  (
    sum(rate(http_requests_total{job="loco_dashboard_api", status=~"5.."}[2m]))
    /
    sum(rate(http_requests_total{job="loco_dashboard_api"}[2m]))
  ) > 0.01
for: 2m
```

Fires when the 5xx error rate exceeds **1%** for 2 consecutive minutes. This is the leading indicator — the SLO breach risk signal. Triggered before the error budget is significantly consumed.

**Alert 2: `LocoAPICriticalDown` (severity: critical)**

```yaml
expr: probe_success{job="blackbox_http", instance=~".*dashboard_api.*"} == 0
for: 1m
```

Fires when the Blackbox Exporter HTTP probe to `http://dashboard_api:9000/` returns 0 (failure) for **1 consecutive minute**. Indicates a complete outage of the dispatcher API — all operator functions unavailable.

This midterm uses exactly two alerts as required (Warning + Critical).

### Triggering the Critical Alert

To demonstrate the `LocoAPICriticalDown` alert firing:

```bash
# Scale the dispatcher API to 0 replicas (simulates outage)
make swarm-trigger-alert
# Equivalent: docker service scale dashboard_stack_dashboard_api=0

# Wait ~1 minute, then check alerts
open http://127.0.0.1:9090/alerts
# LocoAPICriticalDown should be FIRING

# Restore service
make swarm-restore
# Equivalent: docker service scale dashboard_stack_dashboard_api=1
```

The Prometheus Alerts page at `http://127.0.0.1:9090/alerts` will show:

```
LocoAPICriticalDown  FIRING
  severity: critical
  instance: http://dashboard_api:9000/
  "Dispatcher API is completely DOWN"
```

---

## 8. Post-Deployment Fixes

During final validation and live testing, the following production-relevant fixes were applied:

1. **Grafana datasource provisioning fix**  
   Added explicit datasource UID in `grafana/provisioning/datasources/prometheus.yml`:
   - `uid: prometheus`  
   This resolved: `datasource prometheus was not found`.

2. **Frontend endpoint hardcode removal**  
   Removed `localhost` hardcodes in `LocoDashboard` frontend/auth/WS code.  
   Added runtime config endpoint in `LocoDashboard/server.js` (`/runtime-config.js`) with env-driven values:
   - `DASHBOARD_API_HOST` (default `127.0.0.1`)
   - `DASHBOARD_API_PORT` (default `9000`)

3. **LocoApp dashboard endpoint parameterization**  
   `LocoAppBack/main.py` now supports:
   - `DASHBOARD_URL` (highest priority)
   - fallback to `DASHBOARD_HOST` + `DASHBOARD_PORT`  
   This removes coupling to `localhost` defaults.

4. **CORS preflight fix for login**  
   Updated `LocoDashboardBack/main.py` CORS setup:
   - Allowed origins: `localhost`, `127.0.0.1`, `::1` on port `3000`
   - Allowed methods include `OPTIONS`  
   Added env override `CORS_ORIGINS`.

These fixes were validated on running Swarm services and resolved login/preflight and dashboard provisioning errors.

---

## 9. Conclusion

This project demonstrates a complete SRE approach applied to a real-world-inspired application:

| Requirement | Implementation |
|-------------|---------------|
| Custom Dockerfiles | 4 Dockerfiles (2 Python, 2 Node.js) for all services |
| docker-compose.yml | Preserved unchanged for development workflow |
| **BONUS: Docker Swarm** | 3 separate stacks (`dashboard_stack`, `loco_stack`, `monitoring_stack`) |
| SLI/SLO Definition | 2 SLIs on the stable dispatcher API; on-board boards explicitly excluded |
| Error Budget Calculation | 216 min/month (availability) and 432 min/month (latency) |
| Grafana Dashboard | Golden Signals + SLO compliance panels, auto-provisioned |
| Prometheus Alerting | Warning (error rate) and Critical (outage via blackbox) |
| Alert Triggered | `make swarm-trigger-alert` scales API to 0, alert fires in ~1 min |

**Key SRE insight:** The deliberate decision to not instrument the on-board computers and instead use blackbox probing is architecturally correct. It reflects that **reliability is measured from the user's perspective** (the dispatcher), not from inside the system. The BCK-3 boards being temporarily offline is a feature — graceful degradation — not an SLO violation.
