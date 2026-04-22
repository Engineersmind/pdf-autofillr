# 🐳 Docker Deployment Guide

## Overview

**PDF Autofillr uses Docker for isolated, reproducible deployments.** All dependencies, models, and configurations are containerized, ensuring consistent behavior across different environments.

---

## 🎯 Deployment Philosophy

### Isolated Environment
- **Every module runs in its own Docker container**
- **All dependencies bundled** - No system-level conflicts
- **Reproducible builds** - Same image works everywhere
- **Resource isolation** - Control CPU, memory, GPU allocation per container

### Config-Driven Deployment
The **`config.ini`** file controls where your application runs:

```ini
[general]
source_type = local    # or aws, azure, gcp

[mapping]
llm_model = ollama/llama3.1    # or gpt-4o, claude-3-5-sonnet-20241022

[gpu]
gpu_mode = auto    # or cuda, mps, cpu
```

**Same Docker image, different deployments** - Just change the config!

---

## 🏗️ Architecture

### Module-Based Containers

```
┌─────────────────────────────────────────────────────────────┐
│                    DOCKER ARCHITECTURE                       │
└─────────────────────────────────────────────────────────────┘

modules/mapper/
├── Dockerfile              ← Builds mapper container
├── requirements.txt        ← ALL cloud dependencies (AWS+Azure+GCP)
├── config.ini             ← Controls deployment target
└── src/                   ← Application code

modules/chatbot/
├── Dockerfile
├── requirements.txt
├── config.ini
└── src/

modules/rag/
├── Dockerfile
├── requirements.txt
├── config.ini
└── src/

modules/orchestrator/
├── Dockerfile
├── requirements.txt
├── config.ini
└── src/
```

### Single Image, Multiple Clouds

```
┌──────────────────────────────────────────┐
│   One Docker Image (e.g., mapper:1.0)   │
└──────────────────────────────────────────┘
                   │
                   ├─→ Deploy to AWS      (source_type=aws)
                   ├─→ Deploy to Azure    (source_type=azure)
                   ├─→ Deploy to GCP      (source_type=gcp)
                   └─→ Deploy locally     (source_type=local)
```

**No need to rebuild!** Just mount different `config.ini`:

```bash
# AWS deployment
docker run -v /path/to/aws-config.ini:/app/config.ini mapper:1.0

# Azure deployment
docker run -v /path/to/azure-config.ini:/app/config.ini mapper:1.0

# Local deployment
docker run -v /path/to/local-config.ini:/app/config.ini mapper:1.0
```

---

## ⚙️ Configuration-Based Deployment

### Deployment Targets

The `[general]` section controls where data is stored:

```ini
[general]
# Choose your deployment target
source_type = local    # Options: local, aws, azure, gcp
```

### LLM Provider Configuration

The `[mapping]` section controls which LLM to use:

```ini
[mapping]
# Cloud APIs (fast, paid)
llm_model = gpt-4o                                          # OpenAI
llm_model = claude-3-5-sonnet-20241022                     # Anthropic
llm_model = bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0  # AWS Bedrock
llm_model = azure/gpt-4                                    # Azure OpenAI
llm_model = vertex_ai/gemini-pro                           # Google Vertex AI

# Local/Open-Source (free, slower)
llm_model = ollama/llama3.1                                # Ollama
llm_model = ollama/mistral                                 # Ollama (faster)
llm_model = ollama/qwen2.5                                 # Ollama (technical)
```

### GPU Configuration

The `[gpu]` section controls hardware acceleration:

```ini
[gpu]
# GPU mode: auto, cuda, mps, cpu
gpu_mode = auto

# GPU memory limit (MB) - 0 = unlimited
gpu_memory_limit = 6000    # Leave 2GB free for system on 8GB GPU

# Number of GPU layers (Ollama-specific) - -1 = all
num_gpu_layers = -1

# Low VRAM mode (for GPUs < 8GB)
low_vram_mode = false

# GPU device (for multi-GPU systems)
gpu_device = 0
```

---

## 🚀 Deployment Scenarios

### Scenario 1: Local Development (CPU)

**Use Case:** Learning, testing, no GPU available

```ini
[general]
source_type = local

[mapping]
llm_model = ollama/llama3.1    # Small model

[gpu]
gpu_mode = cpu                  # Force CPU
low_vram_mode = false           # Not needed for CPU
```

**Expected Performance:** 60-300 seconds per PDF

**Command:**
```bash
docker run -v $(pwd)/config.ini:/app/config.ini \
  -v $(pwd)/data:/app/data \
  pdf-autofillr-mapper:latest
```

---

### Scenario 2: Local Development (GPU - NVIDIA)

**Use Case:** Development with NVIDIA GPU (better performance)

```ini
[general]
source_type = local

[mapping]
llm_model = ollama/llama3.1

[gpu]
gpu_mode = cuda                 # NVIDIA GPU
gpu_memory_limit = 6000         # 6GB (for 8GB VRAM)
num_gpu_layers = -1             # All layers on GPU
low_vram_mode = false
```

**Expected Performance:** 10-30 seconds per PDF

**Command:**
```bash
docker run --gpus all \
  -v $(pwd)/config.ini:/app/config.ini \
  -v $(pwd)/data:/app/data \
  pdf-autofillr-mapper:latest
```

---

### Scenario 3: Local Development (GPU - Apple Silicon)

**Use Case:** Development on Mac M1/M2/M3

```ini
[general]
source_type = local

[mapping]
llm_model = ollama/llama3.1

[gpu]
gpu_mode = mps                  # Apple Silicon GPU
gpu_memory_limit = 0            # Unlimited
num_gpu_layers = -1
low_vram_mode = false
```

**Expected Performance:** 10-30 seconds per PDF

**Command:**
```bash
docker run \
  -v $(pwd)/config.ini:/app/config.ini \
  -v $(pwd)/data:/app/data \
  pdf-autofillr-mapper:latest
```

---

### Scenario 4: AWS Lambda Deployment

**Use Case:** Serverless production, pay-per-use

```ini
[general]
source_type = aws

[mapping]
llm_model = bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0

[aws]
cache_registry_path = s3://my-bucket/cache/hash_registry.json
output_base_path = s3://my-bucket/output

[gpu]
gpu_mode = cpu                  # Lambda doesn't support GPU
```

**Expected Performance:** 2-5 seconds per PDF (cloud API)

**Deployment:**
```bash
# Build and push to ECR
docker build -t pdf-autofillr-mapper .
aws ecr get-login-password | docker login --username AWS --password-stdin
docker tag pdf-autofillr-mapper:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/mapper:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/mapper:latest

# Create Lambda from ECR image
aws lambda create-function \
  --function-name pdf-mapper \
  --package-type Image \
  --code ImageUri=123456789.dkr.ecr.us-east-1.amazonaws.com/mapper:latest \
  --role arn:aws:iam::123456789:role/lambda-execution
```

---

### Scenario 5: Azure Container Instances

**Use Case:** Scalable cloud deployment on Azure

```ini
[general]
source_type = azure

[mapping]
llm_model = azure/gpt-4

[azure]
cache_registry_path = azure://my-container/cache/hash_registry.json
output_base_path = azure://my-container/output

[gpu]
gpu_mode = cpu                  # Or 'cuda' for GPU-enabled instances
```

**Expected Performance:** 2-5 seconds per PDF (cloud API)

**Deployment:**
```bash
# Build and push to ACR
docker build -t pdf-autofillr-mapper .
az acr login --name myregistry
docker tag pdf-autofillr-mapper:latest myregistry.azurecr.io/mapper:latest
docker push myregistry.azurecr.io/mapper:latest

# Deploy to ACI
az container create \
  --resource-group myResourceGroup \
  --name pdf-mapper \
  --image myregistry.azurecr.io/mapper:latest \
  --cpu 2 --memory 4
```

---

### Scenario 6: Google Cloud Run

**Use Case:** Serverless on GCP with auto-scaling

```ini
[general]
source_type = gcp

[mapping]
llm_model = vertex_ai/gemini-pro

[gcp]
cache_registry_path = gs://my-bucket/cache/hash_registry.json
output_base_path = gs://my-bucket/output

[gpu]
gpu_mode = cpu                  # Cloud Run doesn't support GPU
```

**Expected Performance:** 2-5 seconds per PDF (cloud API)

**Deployment:**
```bash
# Build and push to GCR
docker build -t pdf-autofillr-mapper .
gcloud auth configure-docker
docker tag pdf-autofillr-mapper:latest gcr.io/my-project/mapper:latest
docker push gcr.io/my-project/mapper:latest

# Deploy to Cloud Run
gcloud run deploy pdf-mapper \
  --image gcr.io/my-project/mapper:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

---

### Scenario 7: Kubernetes (Multi-Cloud)

**Use Case:** Enterprise production with auto-scaling, multiple clouds

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pdf-mapper
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pdf-mapper
  template:
    metadata:
      labels:
        app: pdf-mapper
    spec:
      containers:
      - name: mapper
        image: pdf-autofillr-mapper:latest
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
            nvidia.com/gpu: 1      # Request GPU
          limits:
            memory: "8Gi"
            cpu: "4"
            nvidia.com/gpu: 1
        volumeMounts:
        - name: config
          mountPath: /app/config.ini
          subPath: config.ini
      volumes:
      - name: config
        configMap:
          name: mapper-config
```

**Config as ConfigMap:**
```bash
kubectl create configmap mapper-config --from-file=config.ini
kubectl apply -f deployment.yaml
```

---

## 📊 Performance Comparison by Deployment

| Deployment | LLM Provider | GPU Support | Speed (per PDF) | Cost | Use Case |
|------------|--------------|-------------|-----------------|------|----------|
| **Local CPU** | Ollama | ❌ | 60-300s | $0 | Development, testing |
| **Local GPU** | Ollama | ✅ CUDA/MPS | 10-30s | $0 | Development, prototyping |
| **AWS Lambda** | Bedrock | ❌ | 2-5s | $0.01-0.03 | Production, serverless |
| **Azure ACI** | Azure OpenAI | ✅ Optional | 2-5s | $0.01-0.03 | Production, cloud |
| **GCP Cloud Run** | Vertex AI | ❌ | 2-5s | $0.01-0.03 | Production, auto-scale |
| **Kubernetes (GPU)** | Ollama | ✅ CUDA | 10-30s | $0 + infra | Production, private |
| **Kubernetes (Cloud)** | OpenAI/Claude | ❌ | 2-5s | $0.01-0.03 + infra | Production, hybrid |

---

## 🔧 GPU Configuration Deep Dive

### Understanding GPU Settings

```ini
[gpu]
# Auto-detect and use best available hardware
gpu_mode = auto

# Explicit GPU modes:
# - cuda: NVIDIA GPU (requires NVIDIA Docker runtime)
# - mps: Apple Silicon (M1/M2/M3)
# - cpu: Force CPU only (no GPU)

# GPU memory management
gpu_memory_limit = 6000    # Leave headroom for system
# Example calculations:
#   8GB VRAM → set to 6000 (leave 2GB)
#   16GB VRAM → set to 14000 (leave 2GB)
#   24GB VRAM → set to 22000 (leave 2GB)

# Layer offloading (Ollama-specific)
num_gpu_layers = -1        # -1 = all layers, 0 = CPU only
# Common settings:
#   7B models: 35-40 layers
#   13B models: 40-50 layers
#   70B models: 80+ layers (needs 48GB+ VRAM)

# Low VRAM mode (for systems with < 8GB VRAM)
low_vram_mode = true       # Slower but uses less memory
```

### Docker GPU Setup

**NVIDIA GPU (CUDA):**
```bash
# Install nvidia-docker2
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# Run with GPU
docker run --gpus all -v $(pwd)/config.ini:/app/config.ini mapper:latest
```

**Apple Silicon (MPS):**
```bash
# MPS support is automatic in Docker Desktop for Mac
# Just ensure gpu_mode=mps in config.ini
docker run -v $(pwd)/config.ini:/app/config.ini mapper:latest
```

**Multi-GPU Systems:**
```ini
[gpu]
gpu_device = 0    # Use first GPU
# or
gpu_device = 1    # Use second GPU
```

```bash
# Run on specific GPU
docker run --gpus '"device=0"' mapper:latest    # First GPU
docker run --gpus '"device=1"' mapper:latest    # Second GPU
docker run --gpus all mapper:latest             # All GPUs
```

---

## 🔄 Switching Deployments

### Development → Production

**Development (local + Ollama):**
```ini
[general]
source_type = local

[mapping]
llm_model = ollama/llama3.1

[gpu]
gpu_mode = cuda
```

**Production (AWS + Bedrock):**
```ini
[general]
source_type = aws

[mapping]
llm_model = bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0

[aws]
cache_registry_path = s3://prod-bucket/cache/hash_registry.json
output_base_path = s3://prod-bucket/output

[gpu]
gpu_mode = cpu    # Lambda/Fargate don't support GPU
```

**Same Docker image, just different config!**

---

## 📝 Best Practices

### 1. Use Config Inheritance
```bash
# Base config
config.ini

# Environment-specific overrides
config.dev.ini      # Local development
config.staging.ini  # Staging environment
config.prod.ini     # Production

# Mount the right config
docker run -v config.dev.ini:/app/config.ini mapper:latest
```

### 2. Environment Variables Override
Some settings can be overridden with environment variables:
```bash
docker run \
  -e LLM_MODEL=gpt-4o \
  -e SOURCE_TYPE=aws \
  -e GPU_MODE=cpu \
  -v config.ini:/app/config.ini \
  mapper:latest
```

### 3. Resource Limits
Always set resource limits in production:
```bash
docker run \
  --cpus="2.0" \
  --memory="4g" \
  --gpus all \
  mapper:latest
```

### 4. Health Checks
Add health checks to your deployment:
```yaml
# docker-compose.yml
services:
  mapper:
    image: mapper:latest
  healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## 🎯 Summary

✅ **Isolated Environment** - Docker containers ensure consistency  
✅ **Config-Driven** - Change `config.ini`, not code  
✅ **Multi-Cloud Ready** - Same image deploys anywhere  
✅ **GPU Support** - Configurable hardware acceleration  
✅ **Flexible LLMs** - Free local or paid cloud options  
✅ **Performance Tuning** - GPU settings for optimal speed  

**Key Principle:** Build once, deploy anywhere, configure everything.

---

## 📚 Related Documentation

- [Docker Strategy](deployment/DOCKER_STRATEGY.md) - Technical Docker details
- [Free Local LLMs](FREE_LOCAL_LLMS.md) - Open-source LLM options
- [Getting Started](GETTING_STARTED.md) - Quick start guide
- [Configuration Guide](modules/mapper/README.md) - Full config reference
