# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .


# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

RUN groupadd --system botgroup && \
    useradd --system --gid botgroup --no-create-home botuser

WORKDIR /app

COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/tmp/matplotlib

COPY --chown=botuser:botgroup src/ src/
COPY --chown=botuser:botgroup migrations/ migrations/
COPY --chown=botuser:botgroup alembic.ini alembic.ini
COPY --chown=botuser:botgroup docker-entrypoint.sh docker-entrypoint.sh

RUN mkdir -p data logs && \
    chown -R botuser:botgroup data logs && \
    chmod +x docker-entrypoint.sh

USER botuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c \
  "import os,time; f='/tmp/heartbeat'; exit(0 if os.path.exists(f) and time.time()-os.path.getmtime(f)<60 else 1)"

ENTRYPOINT ["./docker-entrypoint.sh"]
