PYTHON = .venv/bin/python
PYTEST = .venv/bin/pytest
RUFF   = .venv/bin/ruff
BLACK  = .venv/bin/black
ALEMBIC = .venv/bin/alembic

.PHONY: test lint fmt migrate

test:
	$(PYTEST) -v

lint:
	$(RUFF) check src tests

fmt:
	$(BLACK) src tests

migrate:
	$(ALEMBIC) upgrade head
