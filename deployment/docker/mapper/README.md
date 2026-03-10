# Mapper Module - Docker Deployment

## Overview

This directory contains Docker configuration for the **Mapper Module**. The Docker image is **universal** - it includes dependencies for all cloud providers (AWS, Azure, GCP) and can be configured at runtime via environment variables.

## 🎯 Strategy

### **One Image, Multiple Sources**

```
Single Docker Build → Universal Image → Configure at Runtime
                                  │
         ┌────────────────────────┼────────────────────┐
         ▼                        ▼                    ▼
    SOURCE_TYPE=local      SOURCE_TYPE=aws      SOURCE_TYPE=azure
    (Local filesystem)     (S3 storage)         (Blob storage)
```

**Benefits**:
- ✅ Build once, deploy anywhere
- ✅ Test locally with any source
- ✅ Switch clouds without rebuilding
- ✅ Consistent behavior across environments

## 📁 Files

```
deployment/docker/mapper/
├── Dockerfile              # Universal image definition
├── docker-compose.yml      # Local testing with docker-compose
├── .env.example           # Environment variable template
├── build.sh               # Build script
├── test.sh                # Test script (all sources)
└── README.md              # This file
```

## 🚀 Quick Start

### 1. **Setup Environment**

```bash
cd deployment/docker/mapper

# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env
```

**Minimum required**:
```bash
SOURCE_TYPE=local
OPENAI_API_KEY=sk-your-key-here
```

### 2. **Build Image**

```bash
./build.sh
```

This creates: `pdf-mapper:latest` (~800MB)

### 3. **Test Image**

```bash
# Test with all configured sources
./test.sh

# Or test manually with docker-compose
docker-compose up
```

### 4. **Access API**

```bash
# Health check
curl http://localhost:8000/health

# Map PDF
curl -X POST http://localhost:8000/map \
  -F "pdf=@../../../data/modules/mapper_sample/input/small_4page.pdf" \
  -F "user_data={\"name\":\"John Doe\"}"
```

## 🔧 Configuration

### Environment Variables

The Docker image is configured via environment variables. See `.env.example` for full list.

**Core Variables**:

| Variable | Required | Values | Description |
|----------|----------|--------|-------------|
| `SOURCE_TYPE` | ✅ Yes | `local`, `aws`, `azure`, `gcp` | Storage backend |
| `OPENAI_API_KEY` | ✅ Yes | `sk-...` | OpenAI API key |
| `AWS_REGION` | ⚠️ If aws | `us-east-1`, etc. | AWS region |
| `AWS_ACCESS_KEY_ID` | ⚠️ If aws | | AWS credentials |
| `AWS_SECRET_ACCESS_KEY` | ⚠️ If aws | | AWS credentials |
| `AZURE_STORAGE_CONNECTION_STRING` | ⚠️ If azure | | Azure Blob connection |
| `GOOGLE_CLOUD_PROJECT` | ⚠️ If gcp | | GCP project ID |
| `LOG_LEVEL` | No | `DEBUG`, `INFO`, `WARNING` | Logging level |

### Source-Specific Configuration

#### **Local (Development)**
```bash
SOURCE_TYPE=local
OPENAI_API_KEY=sk-...
# Data mounted via volumes in docker-compose.yml
```

#### **AWS S3**
```bash
SOURCE_TYPE=aws
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
OPENAI_API_KEY=sk-...
```

#### **Azure Blob Storage**
```bash
SOURCE_TYPE=azure
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
OPENAI_API_KEY=sk-...
```

#### **Google Cloud Storage**
```bash
SOURCE_TYPE=gcp
GOOGLE_CLOUD_PROJECT=my-project
GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-key.json  # Mount key file
OPENAI_API_KEY=sk-...
```

## 🐳 Docker Commands

### Build

```bash
# Standard build
./build.sh

# Custom image name/tag
IMAGE_NAME=my-mapper IMAGE_TAG=v1.0 ./build.sh

# Manual build
docker build -f Dockerfile -t pdf-mapper:latest ../../..
```

### Run

```bash
# With docker-compose (recommended)
docker-compose up

# Manual run (local)
docker run -p 8000:8000 \
  -e SOURCE_TYPE=local \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -v $(pwd)/../../../data:/data \
  pdf-mapper:latest

# Manual run (AWS)
docker run -p 8000:8000 \
  -e SOURCE_TYPE=aws \
  -e AWS_REGION=us-east-1 \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  pdf-mapper:latest
```

### Test

```bash
# Automated test (all sources)
./test.sh

# Manual test
docker run --rm pdf-mapper:latest python -c "import src; print('OK')"
```

### Debug

```bash
# View logs
docker-compose logs -f

# Shell into container
docker-compose exec mapper bash

# Inspect container
docker inspect pdf-mapper
```

## 📊 Image Details

### Size Breakdown

```
Base image (python:3.11-slim):  ~150MB
System dependencies:            ~50MB
Python dependencies:            ~600MB
  - Core (PyMuPDF, etc):       ~400MB
  - AWS SDK (boto3):           ~50MB
  - Azure SDK:                 ~80MB
  - GCP SDK:                   ~70MB
Application code:               ~10MB
─────────────────────────────────────
Total:                          ~800MB
```

**Why include all cloud SDKs?**
- Adds only ~200MB total for all 3 clouds
- Allows switching sources without rebuild
- Simplifies testing and deployment

### Layers

```dockerfile
1. Base image (python:3.11-slim)
2. System packages (gcc, curl)
3. Python dependencies (all clouds)
4. Application code (mapper module)
5. Configuration files
```

## 🧪 Testing

### Local Testing

```bash
# 1. Build image
./build.sh

# 2. Start with docker-compose
docker-compose up -d

# 3. Test health
curl http://localhost:8000/health

# 4. Test mapping
curl -X POST http://localhost:8000/map \
  -F "pdf=@../../../data/modules/mapper_sample/input/small_4page.pdf"

# 5. View logs
docker-compose logs -f

# 6. Stop
docker-compose down
```

### Source Testing

Test the same image with different sources:

```bash
# Test local
docker run -p 8001:8000 -e SOURCE_TYPE=local -e OPENAI_API_KEY=$OPENAI_API_KEY pdf-mapper

# Test AWS
docker run -p 8002:8000 -e SOURCE_TYPE=aws \
  -e AWS_REGION=$AWS_REGION \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  pdf-mapper

# Test Azure
docker run -p 8003:8000 -e SOURCE_TYPE=azure \
  -e AZURE_STORAGE_CONNECTION_STRING="$AZURE_STORAGE_CONNECTION_STRING" \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  pdf-mapper
```

### Module Tests in Container

```bash
# Run pytest inside container
docker run --rm pdf-mapper:latest pytest /app/tests/ -v
```

## 🚢 Deployment

### AWS Lambda

```bash
# 1. Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com

docker tag pdf-mapper:latest $AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/pdf-mapper:latest

docker push $AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/pdf-mapper:latest

# 2. Deploy to Lambda
cd ../../aws/mapper
./deploy.sh
```

### Azure Functions

```bash
# 1. Push to ACR
az acr login --name myregistry

docker tag pdf-mapper:latest myregistry.azurecr.io/pdf-mapper:latest

docker push myregistry.azurecr.io/pdf-mapper:latest

# 2. Deploy to Azure Functions
cd ../../azure/mapper
./deploy.sh
```

### GCP Cloud Run

```bash
# 1. Push to GCR
gcloud auth configure-docker

docker tag pdf-mapper:latest gcr.io/my-project/pdf-mapper:latest

docker push gcr.io/my-project/pdf-mapper:latest

# 2. Deploy to Cloud Run
cd ../../gcp/mapper
./deploy.sh
```

### Self-Hosted (EC2, VM, etc.)

```bash
# 1. Copy docker-compose.yml to server
scp docker-compose.yml .env user@server:/app/

# 2. SSH and start
ssh user@server
cd /app
docker-compose up -d

# 3. Set up reverse proxy (nginx, traefik, etc.)
```

## 🔍 Troubleshooting

### Issue: Container won't start

**Check logs**:
```bash
docker-compose logs mapper
```

**Common causes**:
- Missing environment variables
- Invalid API keys
- Port already in use

**Solution**:
```bash
# Verify .env file
cat .env

# Try different port
docker run -p 9000:8000 ... pdf-mapper
```

### Issue: Health check failing

**Test manually**:
```bash
docker run -it --entrypoint bash pdf-mapper:latest
# Inside container:
python -m uvicorn api_server:app --host 0.0.0.0 --port 8000
```

**Check**:
- Is port 8000 accessible?
- Are dependencies installed?
- Is `api_server.py` present?

### Issue: "Module not found" errors

**Verify Python path**:
```bash
docker run --rm pdf-mapper:latest python -c "import sys; print('\n'.join(sys.path))"
```

**Check if src/ is in path**:
```bash
docker run --rm pdf-mapper:latest ls -la /app/src
```

### Issue: Cloud storage access denied

**AWS**:
- Check IAM permissions
- Verify credentials in .env
- Test with AWS CLI: `aws s3 ls`

**Azure**:
- Check connection string
- Verify storage account exists
- Test with Azure CLI: `az storage blob list`

**GCP**:
- Check service account permissions
- Verify credentials file mounted
- Test with gcloud: `gsutil ls`

## 📚 Related Documentation

- [Deployment Plan](../../DEPLOYMENT_PLAN.md) - Overall deployment strategy
- [Mapper Module](../../../modules/mapper/README.md) - Module documentation
- [AWS Deployment](../../aws/mapper/README.md) - AWS-specific deployment
- [API Documentation](../../../modules/mapper/API_SERVER.md) - API endpoints

## 🆘 Support

**If you encounter issues**:

1. Check troubleshooting section above
2. Review logs: `docker-compose logs -f`
3. Verify environment variables: `docker-compose config`
4. Test with minimal config (local + OpenAI only)
5. Open GitHub issue with:
   - Docker version: `docker --version`
   - Compose version: `docker-compose --version`
   - Error logs
   - Steps to reproduce

## 📝 Notes

- **Image size**: ~800MB (includes all cloud SDKs)
- **Build time**: ~5-10 minutes (depends on network)
- **Startup time**: ~2-3 seconds (local), ~5-10 seconds (Lambda cold start)
- **Memory usage**: ~500MB idle, ~2GB processing large PDFs
- **Recommended**: 2GB RAM, 2 vCPUs for production
