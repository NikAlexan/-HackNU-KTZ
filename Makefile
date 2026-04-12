LOCO_API_KEY          ?= super-secret-key-change-me
LOCO_PORTS            := 8000 8001 8002 8003
SCENARIO              ?= OVERHEAT
STACK_NAME_LOCO       ?= loco_stack
STACK_NAME_DASHBOARD  ?= dashboard_stack
STACK_NAME_MONITORING ?= monitoring_stack

run:
	cd $(CURDIR)/LocoDashboardBack && docker compose up -d
	cd $(CURDIR)/LocoAppBack && docker compose up -d
	cd $(CURDIR)/LocoDashboard && docker compose up -d
	cd $(CURDIR)/LocoPanel && docker compose up -d

stop:
	cd $(CURDIR)/LocoAppBack && docker compose down
	cd $(CURDIR)/LocoDashboardBack && docker compose down
	cd $(CURDIR)/LocoDashboard && docker compose down
	cd $(CURDIR)/LocoPanel && docker compose down

# Trigger incident on all loco instances
# Usage: make incident              → OVERHEAT on all
#        make incident SCENARIO=CRITICAL_ALERT
#        make incident SCENARIO=VOLTAGE_SAG
incident:
	@for port in $(LOCO_PORTS); do \
		echo "→ localhost:$$port  scenario=$(SCENARIO)"; \
		curl -sf -X POST http://localhost:$$port/api/maintenance/incident \
			-H "X-API-Key: $(LOCO_API_KEY)" \
			-H "Content-Type: application/json" \
			-d '{"scenario":"$(SCENARIO)"}' | python3 -m json.tool || true; \
	done

# Clear forced scenario — resume normal simulation
clear-incident:
	@for port in $(LOCO_PORTS); do \
		echo "→ localhost:$$port  clear"; \
		curl -sf -X DELETE http://localhost:$$port/api/maintenance/incident \
			-H "X-API-Key: $(LOCO_API_KEY)" | python3 -m json.tool || true; \
	done

# ── Docker Swarm targets ────────────────────────────────────────────────────

# Initialize Swarm on this node (idempotent)
swarm-init:
	docker swarm init || true

# Build all application images tagged for Swarm deployment
swarm-build:
	docker build -t loco_app_back:swarm      $(CURDIR)/LocoAppBack
	docker build -t loco_dash_back:swarm     $(CURDIR)/LocoDashboardBack
	docker build -t loco_dashboard_ui:swarm  $(CURDIR)/LocoDashboard
	docker build -t loco_panel_ui:swarm      $(CURDIR)/LocoPanel

# Create the shared overlay network (idempotent)
swarm-network:
	docker network create --driver overlay --attachable loco_shared || true

# Register config files into Docker Swarm (idempotent — skips existing)
swarm-configs:
	docker config inspect prometheus_yml      >/dev/null 2>&1 || docker config create prometheus_yml      $(CURDIR)/prometheus/prometheus.yml
	docker config inspect alert_rules_yml     >/dev/null 2>&1 || docker config create alert_rules_yml     $(CURDIR)/prometheus/alert_rules.yml
	docker config inspect grafana_datasources_yml >/dev/null 2>&1 || docker config create grafana_datasources_yml $(CURDIR)/grafana/provisioning/datasources/prometheus.yml
	docker config inspect grafana_dashboards_yml  >/dev/null 2>&1 || docker config create grafana_dashboards_yml  $(CURDIR)/grafana/provisioning/dashboards/dashboard.yml
	docker config inspect grafana_dashboard_json  >/dev/null 2>&1 || docker config create grafana_dashboard_json  $(CURDIR)/grafana/dashboards/loco_digital_twin.json

# Update configs after editing source files (removes old, creates new, redeploys)
swarm-configs-update:
	@for cfg in prometheus_yml alert_rules_yml grafana_datasources_yml grafana_dashboards_yml grafana_dashboard_json; do \
		docker config rm $$cfg 2>/dev/null || true; \
	done
	$(MAKE) swarm-configs
	docker stack deploy --resolve-image never -c $(CURDIR)/docker-stack-dashboard.yml $(STACK_NAME_DASHBOARD)

# Deploy all stacks (dashboard first — MQTT and DB must be up before locos register)
# --resolve-image never: use locally built images, skip registry digest resolution
swarm-deploy: swarm-network swarm-configs
	docker stack deploy --resolve-image never -c $(CURDIR)/docker-stack-dashboard.yml   $(STACK_NAME_DASHBOARD)
	docker stack deploy --resolve-image never -c $(CURDIR)/docker-stack-loco.yml        $(STACK_NAME_LOCO)
	docker stack deploy --resolve-image never -c $(CURDIR)/docker-stack-monitoring.yml  $(STACK_NAME_MONITORING)

# Show running services for all stacks
swarm-status:
	@echo "=== Dashboard Stack ($(STACK_NAME_DASHBOARD)) ===" \
		&& docker stack services $(STACK_NAME_DASHBOARD)
	@echo "" \
		&& echo "=== Loco Stack ($(STACK_NAME_LOCO)) ===" \
		&& docker stack services $(STACK_NAME_LOCO)
	@echo "" \
		&& echo "=== Monitoring Stack ($(STACK_NAME_MONITORING)) ===" \
		&& docker stack services $(STACK_NAME_MONITORING)

# Remove all stacks
swarm-down:
	docker stack rm $(STACK_NAME_LOCO)
	docker stack rm $(STACK_NAME_DASHBOARD)
	docker stack rm $(STACK_NAME_MONITORING)

# Trigger Critical alert: scale dashboard_api to 0 replicas
swarm-trigger-alert:
	docker service scale $(STACK_NAME_DASHBOARD)_dashboard_api=0
	@echo "→ LocoAPICriticalDown will fire in ~1 minute. Check http://127.0.0.1:9090/alerts"

# Restore dashboard_api after alert demo
swarm-restore:
	docker service scale $(STACK_NAME_DASHBOARD)_dashboard_api=1