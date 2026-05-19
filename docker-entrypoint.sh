#!/usr/bin/env bash
set -euo pipefail

mkdir -p data logs

alembic upgrade head

exec python -m src.main
