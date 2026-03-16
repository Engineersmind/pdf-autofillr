# Mapper Module — Universal Dockerfile
# Supports all cloud platforms: AWS, Azure, GCP, Local
# Configure at runtime via SOURCE_TYPE environment variable

FROM python:3.11-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 mapper && chown -R mapper:mapper /app

# ── Dependencies layer (cached separately for fast rebuilds) ─────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application layer ─────────────────────────────────────────────────────────
USER mapper

COPY --chown=mapper:mapper src/           ./src/
COPY --chown=mapper:mapper adapters/      ./adapters/
COPY --chown=mapper:mapper api_server.py  .
COPY --chown=mapper:mapper config.ini.example ./config.ini

ENV PYTHONPATH=/app/src:/app:/app/adapters
ENV PATH=/home/mapper/.local/bin:$PATH

# ── Runtime ───────────────────────────────────────────────────────────────────
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENV SOURCE_TYPE=local \
    LOG_LEVEL=INFO \
    PORT=8000 \
    PYTHONUNBUFFERED=1

CMD ["python", "-m", "uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
