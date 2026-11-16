.PHONY: help check-secrets build-corpus build-index benchmark lint typecheck test run-api run-demo compose-up compose-down

PYTHON ?= python3

help:
	$(PYTHON) scripts/dev.py --help

check-secrets build-corpus build-index benchmark lint typecheck test run-api run-demo:
	$(PYTHON) scripts/dev.py $@

compose-up:
	docker compose -f infra/compose/docker-compose.yml up -d qdrant redis

compose-down:
	docker compose -f infra/compose/docker-compose.yml down
