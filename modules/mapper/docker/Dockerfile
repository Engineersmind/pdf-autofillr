# PDF Autofiller Mapper — Universal Dockerfile
# Supports all platforms via DEPLOY_MODE env var:
#   fastapi  (default) — HTTP server via uvicorn
#   local              — reads from /app/data/input, writes to /app/data/output
#   cli                — run once from command line args

FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN useradd -m -u 1000 mapper && chown -R mapper:mapper /app

# ── Dependencies (cached layer) ───────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application ───────────────────────────────────────────────────────────────
USER mapper

COPY --chown=mapper:mapper src/          ./src/
COPY --chown=mapper:mapper entrypoints/  ./entrypoints/
COPY --chown=mapper:mapper adapter_src/  ./adapter_src/
COPY --chown=mapper:mapper pyproject.toml .

ENV PYTHONPATH=/app/src:/app:/app/adapter_src
ENV PATH=/home/mapper/.local/bin:$PATH

# ── Runtime defaults ──────────────────────────────────────────────────────────
ENV DEPLOY_MODE=fastapi \
    LOG_LEVEL=INFO \
    PORT=8000 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

CMD if [ "$DEPLOY_MODE" = "local" ]; then \
      exec python entrypoints/local.py; \
    elif [ "$DEPLOY_MODE" = "cli" ]; then \
      exec python entrypoints/cli.py; \
    else \
      exec python -m uvicorn entrypoints.fastapi_app:app --host 0.0.0.0 --port ${PORT}; \
    fi
