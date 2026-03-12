# ============================================
# PDF Autofiller Mapper - Dockerfile
# ============================================
# Multi-stage build for optimized image size
# 
# Build: docker build -t pdf-autofiller-mapper -f deployment/docker/Dockerfile .
# Run:   docker run -p 8000:8000 -v $(pwd)/data:/app/data pdf-autofiller-mapper

# Stage 1: Base image with Python and system dependencies
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    curl \
    default-jre \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Build dependencies
FROM base as builder

WORKDIR /build

# Copy requirements first for better caching
COPY modules/mapper/requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 3: Runtime image
FROM base as runtime

# Create app directory
WORKDIR /app

# Create directories for data
RUN mkdir -p /app/data/input \
             /app/data/output \
             /app/data/cache \
             /tmp/processing

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY modules/mapper/ /app/

# Ensure Python can find packages
ENV PATH=/root/.local/bin:$PATH \
    PYTHONPATH=/app:$PYTHONPATH

# Expose HTTP port
EXPOSE 8000

# Set default environment variables
ENV HTTP_HOST=0.0.0.0 \
    HTTP_PORT=8000 \
    STORAGE_TYPE=local \
    DATA_DIR=/app/data \
    PROCESSING_DIR=/tmp/processing

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command: Run HTTP server
CMD ["python", "-m", "entrypoints.http_server"]

# Alternative commands:
# CLI mode:    docker run ... pdf-autofiller-mapper python -m test_local_entrypoint
# HTTP mode:   docker run ... pdf-autofiller-mapper python -m entrypoints.http_server
