# PDF Autofiller Mapper - Docker Deployment Guide

## Quick Start

### 1. Build the Docker Image

```bash
cd /Users/raghava/Documents/EMC/pdf-autofillr
docker build -t pdf-autofiller-mapper -f modules/mapper/deployment/docker/Dockerfile .
```

### 2. Run the Container

```bash
# Run with data directory mounted
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  --name mapper \
  pdf-autofiller-mapper
```

### 3. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Make embed file
curl -X POST http://localhost:8000/make-embed-file \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 553,
    "session_id": "086d6670-81e5-47f4-aecb-e4f7c3ba2a83",
    "pdf_doc_id": 990,
    "use_second_mapper": true
  }'
```

---

## Using Docker Compose (Recommended)

### Start the Service

```bash
cd modules/mapper/deployment/docker
docker-compose up -d
```

### View Logs

```bash
docker-compose logs -f
```

### Stop the Service

```bash
docker-compose down
```

---

## Configuration

### Environment Variables

Create a `.env` file or pass environment variables:

```bash
# Server configuration
HTTP_HOST=0.0.0.0
HTTP_PORT=8000

# Storage configuration
STORAGE_TYPE=local
DATA_DIR=/app/data
PROCESSING_DIR=/tmp/processing

# Optional: LLM configuration
OPENAI_API_KEY=your-api-key-here
LLM_MODEL=gpt-4o
USE_SECOND_MAPPER=true
```

### Volume Mounts

```bash
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \              # Data directory
  -v $(pwd)/config.ini:/app/config.ini \  # Config file
  -v $(pwd)/.env:/app/.env \              # Environment file
  --name mapper \
  pdf-autofiller-mapper
```

---

## Deployment Options

### Option 1: Standalone Docker Container

```bash
# Build
docker build -t pdf-autofiller-mapper -f deployment/docker/Dockerfile .

# Run
docker run -d -p 8000:8000 -v $(pwd)/data:/app/data pdf-autofiller-mapper

# Stop
docker stop mapper && docker rm mapper
```

### Option 2: Docker Compose

```bash
# Start
docker-compose up -d

# Scale (if needed)
docker-compose up -d --scale mapper=3

# Stop
docker-compose down
```

### Option 3: AWS ECS/Fargate

```bash
# Tag for ECR
docker tag pdf-autofiller-mapper:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/mapper:latest

# Push to ECR
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/mapper:latest

# Deploy to ECS (use provided task definition)
aws ecs update-service --cluster mapper-cluster --service mapper --force-new-deployment
```

### Option 4: Kubernetes

```bash
# Build and push
docker build -t your-registry/pdf-autofiller-mapper:v1.0.0 .
docker push your-registry/pdf-autofiller-mapper:v1.0.0

# Deploy to K8s (use provided manifests)
kubectl apply -f deployment/k8s/
```

---

## File Structure in Container

```
/app/
├── config.ini                 # Configuration file
├── .env                       # Environment variables
├── entrypoints/
│   ├── local.py              # CLI entrypoint
│   ├── http_server.py        # HTTP API entrypoint (DEFAULT)
│   └── aws_lambda_handler.py # Lambda entrypoint
├── src/                      # Source code
├── data/                     # Mounted volume
│   ├── input/               # Input files
│   ├── output/              # Output files
│   └── cache/               # Cache files
└── /tmp/processing/         # Temporary processing directory
```

---

## Health Check

The container includes a health check that runs every 30 seconds:

```bash
# Manual health check
docker exec mapper curl -f http://localhost:8000/health

# View health status
docker ps --format "table {{.Names}}\t{{.Status}}"
```

---

## Logs

### View Container Logs

```bash
# All logs
docker logs mapper

# Follow logs
docker logs -f mapper

# Last 100 lines
docker logs --tail 100 mapper

# With timestamps
docker logs -t mapper
```

### Log to File

```bash
# Redirect logs to file
docker logs mapper > mapper.log 2>&1
```

---

## Performance Tuning

### Resource Limits

```bash
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  --memory="4g" \
  --cpus="2.0" \
  --name mapper \
  pdf-autofiller-mapper
```

### Docker Compose Resource Limits

```yaml
services:
  mapper:
    # ... other config ...
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs mapper

# Check events
docker events --filter container=mapper

# Inspect container
docker inspect mapper
```

### Permission Issues

```bash
# Run with current user
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  --user $(id -u):$(id -g) \
  --name mapper \
  pdf-autofiller-mapper
```

### Network Issues

```bash
# Check if port is already in use
lsof -i :8000

# Use different port
docker run -d -p 8080:8000 -v $(pwd)/data:/app/data pdf-autofiller-mapper
```

### Out of Memory

```bash
# Increase memory limit
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  --memory="8g" \
  --memory-swap="10g" \
  --name mapper \
  pdf-autofiller-mapper
```

---

## Maintenance

### Update Container

```bash
# Pull latest image
docker pull pdf-autofiller-mapper:latest

# Stop old container
docker stop mapper && docker rm mapper

# Start new container
docker run -d -p 8000:8000 -v $(pwd)/data:/app/data pdf-autofiller-mapper:latest
```

### Backup Data

```bash
# Backup data directory
docker run --rm -v mapper-data:/data -v $(pwd):/backup alpine tar czf /backup/mapper-data-backup.tar.gz -C /data .
```

### Clean Up

```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Remove all
docker system prune -a
```

---

## Production Recommendations

1. **Use Docker Compose** for easier management
2. **Set resource limits** to prevent resource exhaustion
3. **Enable health checks** for automatic recovery
4. **Mount volumes** for data persistence
5. **Use environment variables** instead of hardcoding config
6. **Enable logging** to external system (e.g., CloudWatch, ELK)
7. **Set restart policy** to `unless-stopped` or `always`
8. **Use secrets management** for API keys (Docker secrets, AWS Secrets Manager)
9. **Run behind reverse proxy** (Nginx, Traefik) for SSL/TLS
10. **Monitor** with Prometheus/Grafana

---

## Security

### Run as Non-Root User

```dockerfile
# Add to Dockerfile
RUN useradd -m -u 1000 mapper
USER mapper
```

### Use Secrets

```bash
# Create secret
echo "your-api-key" | docker secret create openai_api_key -

# Use in container
docker service create \
  --secret openai_api_key \
  pdf-autofiller-mapper
```

### Network Isolation

```bash
# Create isolated network
docker network create --driver bridge mapper-net

# Run container in isolated network
docker run -d \
  --network mapper-net \
  -p 8000:8000 \
  pdf-autofiller-mapper
```

---

## Next Steps

1. ✅ Build and test Docker image locally
2. ✅ Deploy to staging environment
3. ✅ Run integration tests
4. ✅ Deploy to production
5. ✅ Set up monitoring and alerting
6. ✅ Create CI/CD pipeline
