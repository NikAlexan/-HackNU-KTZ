LOCO_API_KEY ?= super-secret-key-change-me
LOCO_PORTS   := 8000 8001 8002 8003
SCENARIO     ?= OVERHEAT

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