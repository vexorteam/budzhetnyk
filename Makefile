PYTHON  = .venv/bin/python
PYTEST  = .venv/bin/pytest
RUFF    = .venv/bin/ruff
BLACK   = .venv/bin/black
ALEMBIC = .venv/bin/alembic

.PHONY: test test-cov lint fmt migrate \
        build up down logs restart shell backup

# ── Dev ───────────────────────────────────────────────────────────────────────

test:
	$(PYTEST) -v

test-cov:
	$(PYTEST) --cov=src --cov-report=term-missing

lint:
	$(RUFF) check src tests

fmt:
	$(BLACK) src tests

migrate:
	$(ALEMBIC) upgrade head

# ── Docker ───────────────────────────────────────────────────────────────────

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f bot

restart:
	docker compose restart bot

shell:
	docker compose exec bot bash

# ── Ops ──────────────────────────────────────────────────────────────────────

backup:
	./scripts/backup.sh
