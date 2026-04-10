# PDF Autofiller Mapper — Universal Dockerfile
# Supports all platforms via DEPLOY_MODE env var:
#   fastapi  (default) — HTTP server via uvicorn
#   local              — reads from /app/data/input, writes to /app/data/output
#   cli                — run once from command line args

# ── Stage 1: Build Java JARs ──────────────────────────────────────────────────
FROM maven:3.9-eclipse-temurin-17 AS java-builder

WORKDIR /build
COPY src/pdf_autofillr_mapper/java_utils/ ./java_utils/
RUN cd java_utils && mvn -q package -DskipTests

# ── Stage 2: Runtime image ────────────────────────────────────────────────────
FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN useradd -m -u 1000 mapper && chown -R mapper:mapper /app

# ── Dependencies (cached layer) ───────────────────────────────────────────────
COPY requirements-full.txt .
RUN pip install --no-cache-dir -r requirements-full.txt

# ── Application ───────────────────────────────────────────────────────────────
USER mapper

COPY --chown=mapper:mapper src/          ./src/
COPY --chown=mapper:mapper entrypoints/  ./entrypoints/
COPY --chown=mapper:mapper adapter_src/  ./adapter_src/
COPY --chown=mapper:mapper pyproject.toml .

# Copy compiled JARs from build stage into the location embed_keys.py checks
COPY --from=java-builder --chown=mapper:mapper \
    /build/java_utils/form_field_rebuilder/target/form_field_rebuilder-1.0.0-jar-with-dependencies.jar \
    ./src/pdf_autofillr_mapper/assets/rebuilder.jar
COPY --from=java-builder --chown=mapper:mapper \
    /build/java_utils/form_field_filler/target/form_field_filler-1.0.0-jar-with-dependencies.jar \
    ./src/pdf_autofillr_mapper/assets/filler.jar
COPY --from=java-builder --chown=mapper:mapper \
    /build/java_utils/form_field_refresher/target/form_field_refresher-1.0.0-jar-with-dependencies.jar \
    ./src/pdf_autofillr_mapper/assets/refresher.jar

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
