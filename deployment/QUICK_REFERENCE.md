# Quick Reference: Deployment Strategy

## 🎯 Core Answer to Your Questions

### ✅ **YES - One Docker Image for Multiple Sources!**

```
Single Dockerfile → Builds Universal Image → Deploy Anywhere
                                  │
         ┌────────────────────────┼────────────────────┐
         ▼                        ▼                    ▼
    AWS Lambda              Azure Functions      GCP Cloud Run
    (source=aws)            (source=azure)       (source=gcp)
```

---

## 📦 setup.py vs pyproject.toml

| Feature | setup.py | pyproject.toml |
|---------|----------|----------------|
| **Format** | Python script | TOML config |
| **When to use** | Complex builds, dynamic logic | Simple projects, modern tools |
| **Your case** | ✅ Current choice (fine!) | Could migrate later |

**Verdict**: Keep using `setup.py` for now. Works great!

---

## 🏗️ Deployment Flow

### Phase 1: Local Testing ✅ (Already Working)
```bash
cd modules/mapper
pytest tests/  # Module tests
cd ../..
pytest tests/integration/  # Integration tests
```

### Phase 2: Docker (Universal) 🔵 (Next Step)
```bash
# Build ONE image
docker build -t pdf-mapper:universal -f deployment/docker/Dockerfile .

# Test with different sources
docker run -e SOURCE_TYPE=local pdf-mapper:universal
docker run -e SOURCE_TYPE=aws pdf-mapper:universal
docker run -e SOURCE_TYPE=azure pdf-mapper:universal
```

### Phase 3: AWS Lambda 🔴 (Planned)
```bash
# Push same image to ECR
docker push $AWS_ECR/pdf-mapper:latest

# Deploy to Lambda
./deployment/aws/mapper/deploy.sh

# Test
curl https://xxx.execute-api.us-east-1.amazonaws.com/prod/health
```

### Phase 4: SDK Usage (After Lambda Deployed)
```bash
# Configure SDK to point to Lambda
echo "API_URL=https://xxx.execute-api.us-east-1.amazonaws.com/prod" > sdks/python/.env

# Use SDK
pdf-autofiller map test.pdf
```

---

## 🔑 Key Configuration

### Dockerfile (Universal)
```dockerfile
FROM python:3.11-slim

# Install ALL cloud SDKs (AWS + Azure + GCP)
RUN pip install boto3 azure-storage-blob google-cloud-storage

# Runtime: Environment variable determines which cloud
ENV SOURCE_TYPE=local  # Override at runtime
```

### At Deployment
```bash
# AWS Lambda
docker run -e SOURCE_TYPE=aws -e CACHE_PATH=s3://bucket/... pdf-mapper

# Azure Functions
docker run -e SOURCE_TYPE=azure -e CACHE_PATH=azure://container/... pdf-mapper

# GCP Cloud Run
docker run -e SOURCE_TYPE=gcp -e CACHE_PATH=gs://bucket/... pdf-mapper
```

---

## 📋 Test Hierarchy (As You Requested)

```
1. Module Tests (modules/mapper/tests/)
   ↓ Must pass before Docker
   
2. Docker Local Tests (with source=local)
   ↓ Must pass before AWS deployment
   
3. AWS Lambda Tests (deployed endpoint)
   ↓ Must pass before SDK usage
   
4. SDK Tests (pointing to Lambda)
   ↓ Must pass before E2E
   
5. Integration Tests (tests/integration/)
   ✅ Full flow: SDK → Lambda → S3
```

---

## 📂 File Structure (To Create)

```
deployment/
├── DEPLOYMENT_PLAN.md          ✅ Created (comprehensive plan)
├── docker/
│   ├── Dockerfile              🔵 Next: Universal image
│   ├── docker-compose.yml      🔵 Next: Local testing
│   └── README.md               🔵 Next: Docker docs
├── aws/
│   └── mapper/
│       ├── deploy.sh           🔴 Planned: Deployment script
│       ├── setup_infra.sh      🔴 Planned: Create S3, ECR, IAM
│       ├── lambda_config.json  🔴 Planned: Lambda settings
│       └── README.md           🔴 Planned: AWS-specific docs
├── azure/
│   └── mapper/
│       └── (similar structure)
└── gcp/
    └── mapper/
        └── (similar structure)
```

---

## 🎯 Immediate Next Steps

### Option A: Start with Docker (Recommended)
```bash
# 1. Create Dockerfile
# 2. Build image
# 3. Test locally with all sources
# 4. Verify module tests pass in container
# 5. Then move to AWS
```

### Option B: Go Straight to AWS
```bash
# 1. Create Dockerfile + AWS scripts together
# 2. Test locally briefly
# 3. Deploy to Lambda immediately
# 4. Debug in cloud
```

**Recommendation**: **Option A** - Test Docker thoroughly locally first!

---

## 💡 Key Decisions Made

1. ✅ **Single Docker Image**: Yes, one image for all platforms
2. ✅ **Configuration Method**: Environment variables at runtime
3. ✅ **Test Order**: Module → Docker → Lambda → SDK → Integration
4. ✅ **Deployment Target**: Start with AWS Lambda (Docker-based)
5. ✅ **Alternative**: Same image can run on EC2 if needed

---

## 🚀 Want to Start?

**Ready to create the Docker setup?** I can:
1. Create the universal Dockerfile
2. Create docker-compose.yml for local testing
3. Create deployment scripts for AWS Lambda
4. Create test scripts to verify each phase

Just let me know! 🎯
