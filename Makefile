run:
	cd $(CURDIR)/LocoApp && docker compose up -d
	cd $(CURDIR)/LocoDashboard && docker compose up -d

stop:
	cd $(CURDIR)/LocoApp && docker compose down
	cd $(CURDIR)/LocoDashboard && docker compose down