# Mapper Module - Dockerfile
# Universal image supporting all cloud providers (AWS, Azure, GCP, Local)
# Configuration via environment variables at runtime

FROM python:3.11-slim AS base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 mapper && chown -R mapper:mapper /app
USER mapper

# Copy requirements files
COPY --chown=mapper:mapper modules/mapper/requirements.txt ./requirements.txt
COPY --chown=mapper:mapper modules/mapper/requirements-api.txt ./requirements-api.txt
COPY --chown=mapper:mapper modules/mapper/requirements-aws.txt ./requirements-aws.txt
COPY --chown=mapper:mapper modules/mapper/requirements-azure.txt ./requirements-azure.txt
COPY --chown=mapper:mapper modules/mapper/requirements-gcp.txt ./requirements-gcp.txt

# Install ALL dependencies (universal image)
# This makes the image work with any cloud provider
RUN pip install --no-cache-dir --user \
    -r requirements.txt \
    -r requirements-api.txt \
    -r requirements-aws.txt \
    -r requirements-azure.txt \
    -r requirements-gcp.txt

# Copy mapper module source code
COPY --chown=mapper:mapper modules/mapper/src ./src
COPY --chown=mapper:mapper modules/mapper/adapter_src ./adapter_src
COPY --chown=mapper:mapper modules/mapper/config.ini.example ./config.ini

# Copy API server
COPY --chown=mapper:mapper modules/mapper/api_server.py ./api_server.py

# Set Python path
ENV PYTHONPATH=/app/src:/app
ENV PATH=/home/mapper/.local/bin:$PATH

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default configuration (override via environment variables)
ENV SOURCE_TYPE=local
ENV LOG_LEVEL=INFO
ENV PORT=8000

# Run API server
# For Lambda, this will be overridden by Lambda runtime
CMD ["python", "-m", "uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
