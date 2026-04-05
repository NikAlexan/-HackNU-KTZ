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