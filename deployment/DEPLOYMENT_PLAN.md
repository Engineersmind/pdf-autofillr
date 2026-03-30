# PDF Autofillr - Deployment Plan
**Status**: 🟡 Planning Phase  
**Last Updated**: March 10, 2026  
**Focus**: Mapper Module → AWS Lambda (Docker)

---

## 🎯 Deployment Strategy Overview

### Core Principle: **One Docker Image, Multiple Platforms**

```
┌─────────────────────────────────────────────────────────────────┐
│                    SINGLE DOCKER IMAGE                           │
│  (Multi-cloud capable, source-agnostic, all dependencies)       │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  AWS Lambda   │     │ Azure Func    │     │ GCP Cloud Run │
│               │     │               │     │               │
│ source=aws    │     │ source=azure  │     │ source=gcp    │
│ S3 storage    │     │ Blob storage  │     │ GCS storage   │
└───────────────┘     └───────────────┘     └───────────────┘
```

**Why This Works**:
- ✅ **Single Dockerfile** → Less maintenance
- ✅ **Runtime configuration** → Environment variables
- ✅ **All cloud SDKs included** → No rebuild needed
- ✅ **Test once, deploy anywhere** → Consistency

---

## 🏗️ Phase 1: Local Development (Current State)

**Status**: ✅ **WORKING**

```bash
# Already tested and working
cd modules/mapper
python -m pytest tests/          # Module tests pass
cd ../../
python -m pytest tests/integration/  # Integration tests
```

**Components**:
- ✅ Mapper module code (`modules/mapper/src/`)
- ✅ Config file (`modules/mapper/config.ini`)
- ✅ Module tests (`modules/mapper/tests/`)
- ✅ Integration tests (`tests/integration/`)
- ✅ Sample data (`data/modules/mapper_sample/`)

**Verification**:
```bash
# Test locally before Docker
source_type = local
pytest modules/mapper/tests/ -v
```

---

## 🏗️ Phase 2: Docker Image (Universal)

**Status**: 🔵 **NEXT STEP**

### 2.1 Create Unified Dockerfile

**Location**: `deployment/docker/Dockerfile` (ONE file for all)

**Strategy**:
```dockerfile
FROM python:3.11-slim

# Install ALL cloud dependencies (AWS + Azure + GCP)
RUN pip install \
    boto3 \
    azure-storage-blob azure-identity \
    google-cloud-storage \
    fastapi uvicorn \
    pymupdf pillow litellm

# Copy mapper module
COPY modules/mapper /app
WORKDIR /app

# Expose API port
EXPOSE 8000

# Runtime configuration via env vars
CMD ["python", "-m", "uvicorn", "orchestrator:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Benefits**:
- ✅ One image for ALL platforms
- ✅ ~500MB (optimized with slim base)
- ✅ No rebuild when switching platforms
- ✅ Easy to test locally before cloud deployment

### 2.2 Configuration Strategy

**Option A: Environment Variables** (Recommended for Lambda)
```bash
docker run \
  -e SOURCE_TYPE=aws \
  -e AWS_REGION=us-east-1 \
  -e OPENAI_API_KEY=sk-... \
  -e CACHE_REGISTRY_PATH=s3://bucket/cache/registry.json \
  pdf-mapper:latest
```

**Option B: Config File Mount** (Good for local/EC2)
```bash
docker run \
  -v /path/to/config.ini:/app/config.ini \
  -e CONFIG_PATH=/app/config.ini \
  pdf-mapper:latest
```

**Option C: Hybrid** (Best flexibility)
- Base config in image
- Override with env vars
- Priority: ENV > Mounted Config > Built-in Config

### 2.3 Docker Testing

**Test Sequence**:
```bash
# 1. Build image
cd deployment/docker
docker build -t pdf-mapper:latest -f Dockerfile ../..

# 2. Test with local source
docker run -p 8000:8000 \
  -v $(pwd)/../../data:/data \
  -e SOURCE_TYPE=local \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  pdf-mapper:latest

# 3. Test health endpoint
curl http://localhost:8000/health

# 4. Test mapping endpoint
curl -X POST http://localhost:8000/map \
  -F "pdf=@../../data/modules/mapper_sample/input/small_4page.pdf" \
  -F "user_data={\"name\":\"John\"}"

# 5. Run tests inside container
docker run pdf-mapper:latest pytest tests/ -v
```

**Success Criteria**:
- ✅ Container starts without errors
- ✅ Health endpoint returns 200
- ✅ Module tests pass inside container
- ✅ Can process sample PDF

---

## 🏗️ Phase 3: AWS Lambda Deployment

**Status**: 🔴 **PLANNED**

### 3.1 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS INFRASTRUCTURE                       │
└─────────────────────────────────────────────────────────────────┘

  User/SDK Request
        │
        ▼
┌─────────────────┐
│  API Gateway    │ ← REST API (https://...)
│  (REST API)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Lambda         │ ← Docker image (ECR)
│  (Mapper)       │    • source_type=aws
│                 │    • Timeout: 5 min
│  Docker Runtime │    • Memory: 2GB
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  S3 Buckets     │
│                 │
│  • Input PDFs   │
│  • Output PDFs  │
│  • Cache        │
│  • RAG data     │
└─────────────────┘

┌─────────────────┐
│  IAM Roles      │
│                 │
│  • S3 Read/Write│
│  • CloudWatch   │
│  • Secrets Mgr  │
└─────────────────┘
```

### 3.2 Required AWS Resources

**Must Create Before Deployment**:

1. **ECR Repository** (Store Docker image)
   ```bash
   aws ecr create-repository --repository-name pdf-mapper
   ```

2. **S3 Buckets** (Storage)
   ```bash
   # Production bucket
   aws s3 mb s3://pdf-autofiller-prod
   
   # Create folder structure
   aws s3api put-object --bucket pdf-autofiller-prod --key cache/
   aws s3api put-object --bucket pdf-autofiller-prod --key users/
   ```

3. **IAM Role** (Lambda execution)
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "s3:GetObject",
           "s3:PutObject",
           "s3:ListBucket"
         ],
         "Resource": [
           "arn:aws:s3:::pdf-autofiller-prod/*"
         ]
       },
       {
         "Effect": "Allow",
         "Action": [
           "logs:CreateLogGroup",
           "logs:CreateLogStream",
           "logs:PutLogEvents"
         ],
         "Resource": "arn:aws:logs:*:*:*"
       }
     ]
   }
   ```

4. **Secrets Manager** (API keys)
   ```bash
   aws secretsmanager create-secret \
     --name pdf-mapper/openai-key \
     --secret-string '{"OPENAI_API_KEY":"sk-..."}'
   ```

5. **Lambda Function** (Docker-based)
   ```bash
   aws lambda create-function \
     --function-name pdf-mapper \
     --package-type Image \
     --code ImageUri=123456789.dkr.ecr.us-east-1.amazonaws.com/pdf-mapper:latest \
     --role arn:aws:iam::123456789:role/lambda-pdf-mapper \
     --timeout 300 \
     --memory-size 2048 \
     --environment Variables={SOURCE_TYPE=aws,AWS_REGION=us-east-1}
   ```

6. **API Gateway** (REST endpoints)
   ```bash
   aws apigateway create-rest-api \
     --name pdf-mapper-api \
     --endpoint-configuration types=REGIONAL
   ```

### 3.3 Deployment Scripts

**Create**: `deployment/aws/mapper/deploy.sh`

```bash
#!/bin/bash
# AWS Lambda Deployment Script for Mapper Module

set -e  # Exit on error

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="pdf-mapper"
LAMBDA_FUNCTION="pdf-mapper"
S3_BUCKET="pdf-autofiller-prod"

echo "🚀 Deploying Mapper Module to AWS Lambda..."

# Step 1: Build Docker image
echo "📦 Building Docker image..."
cd ../../..  # Go to repo root
docker build -t $ECR_REPO:latest -f deployment/docker/Dockerfile .

# Step 2: Push to ECR
echo "☁️  Pushing to ECR..."
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

docker tag $ECR_REPO:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest

docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest

# Step 3: Update Lambda function
echo "⚡ Updating Lambda function..."
aws lambda update-function-code \
  --function-name $LAMBDA_FUNCTION \
  --image-uri $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest

# Step 4: Wait for update to complete
echo "⏳ Waiting for Lambda to update..."
aws lambda wait function-updated --function-name $LAMBDA_FUNCTION

# Step 5: Test deployment
echo "✅ Testing deployment..."
aws lambda invoke \
  --function-name $LAMBDA_FUNCTION \
  --payload '{"path":"/health","httpMethod":"GET"}' \
  response.json

cat response.json
rm response.json

echo "🎉 Deployment complete!"
echo "API Gateway URL: https://xxx.execute-api.$AWS_REGION.amazonaws.com/prod"
```

### 3.4 Configuration for Lambda

**Lambda Environment Variables**:
```bash
SOURCE_TYPE=aws
AWS_REGION=us-east-1
CACHE_REGISTRY_PATH=s3://pdf-autofiller-prod/cache/hash_registry.json
OUTPUT_BASE_PATH=s3://pdf-autofiller-prod
RAG_BUCKET_NAME=pdf-autofiller-prod
OPENAI_API_KEY_SECRET=pdf-mapper/openai-key  # Reference to Secrets Manager
LLM_MODEL=gpt-4o
LLM_TEMPERATURE=0.05
LLM_TIMEOUT=300
```

**Lambda Configuration**:
- **Timeout**: 300 seconds (5 minutes)
- **Memory**: 2048 MB (adjust based on PDF size)
- **Ephemeral Storage**: 512 MB (for /tmp)
- **Concurrency**: Reserved 10 (prevent cold starts)

### 3.5 Testing Strategy

**Before AWS Deployment**:
```bash
# 1. Test module locally
cd modules/mapper
pytest tests/ -v

# 2. Test integration locally
cd ../..
pytest tests/integration/ -v

# 3. Test Docker locally (with AWS config)
docker run -p 8000:8000 \
  -e SOURCE_TYPE=aws \
  -e AWS_REGION=us-east-1 \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  pdf-mapper:latest

# 4. Test health endpoint
curl http://localhost:8000/health

# 5. Test mapping with S3 (if bucket exists)
curl -X POST http://localhost:8000/map \
  -F "pdf=@data/modules/mapper_sample/input/small_4page.pdf" \
  -F "user_data={}"
```

**After AWS Deployment**:
```bash
# 1. Test Lambda directly
aws lambda invoke \
  --function-name pdf-mapper \
  --payload '{"path":"/health","httpMethod":"GET"}' \
  response.json

# 2. Test via API Gateway
GATEWAY_URL="https://xxx.execute-api.us-east-1.amazonaws.com/prod"
curl $GATEWAY_URL/health

# 3. Test mapping endpoint
curl -X POST $GATEWAY_URL/map \
  -H "x-api-key: YOUR_API_KEY" \
  -F "pdf=@test.pdf" \
  -F "user_data={\"name\":\"John\"}"

# 4. Test with SDK (after deployment verified)
cd sdks/python
pip install -e .
pdf-autofiller map test.pdf --api-url $GATEWAY_URL
```

---

## 🏗️ Phase 4: SDK Usage (After Module Setup)

**Status**: 🟡 **After Phase 3**

### 4.1 Prerequisite: Verify Module Deployment

**Before using SDK, ensure**:
```bash
# ✅ Lambda deployed
aws lambda get-function --function-name pdf-mapper

# ✅ API Gateway configured
curl https://xxx.execute-api.us-east-1.amazonaws.com/prod/health

# ✅ S3 buckets accessible
aws s3 ls s3://pdf-autofiller-prod/

# ✅ Environment variables set
aws lambda get-function-configuration --function-name pdf-mapper | grep SOURCE_TYPE
```

### 4.2 SDK Configuration

**SDK must point to deployed API**:

`sdks/python/.env`:
```bash
API_URL=https://xxx.execute-api.us-east-1.amazonaws.com/prod
API_KEY=your-api-gateway-key  # If using API key auth
```

### 4.3 SDK Testing

```bash
# Install SDK
cd sdks/python
pip install -e .

# Test CLI
pdf-autofiller map test.pdf

# Test Python API
python examples/basic_usage.py
```

---

## 🏗️ Phase 5: Integration Testing

**Status**: 🔴 **After Phase 4**

### 5.1 Test Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│  LEVEL 1: Module Tests (Unit)                           │
│  Location: modules/mapper/tests/                        │
│  Purpose: Test individual functions                     │
│  Run: pytest modules/mapper/tests/                      │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│  LEVEL 2: Integration Tests (System)                    │
│  Location: tests/integration/                           │
│  Purpose: Test module interactions                      │
│  Run: pytest tests/integration/                         │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│  LEVEL 3: E2E Tests (Full Stack)                        │
│  Location: tests/e2e/                                   │
│  Purpose: Test SDK → API → Module → Storage             │
│  Run: pytest tests/e2e/ --api-url=https://...          │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Integration Test Requirements

**Create**: `tests/integration/test_aws_deployment.py`

```python
import pytest
import boto3
import requests
from pathlib import Path

@pytest.fixture
def api_url():
    """Get API Gateway URL from environment or config"""
    return os.getenv("API_URL", "http://localhost:8000")

@pytest.fixture
def s3_client():
    """S3 client for verifying outputs"""
    return boto3.client("s3")

def test_module_deployed(api_url):
    """Test that module is accessible"""
    response = requests.get(f"{api_url}/health")
    assert response.status_code == 200

def test_end_to_end_mapping(api_url, s3_client):
    """Test full PDF mapping workflow"""
    # Upload PDF
    pdf_path = Path("data/modules/mapper_sample/input/small_4page.pdf")
    response = requests.post(
        f"{api_url}/map",
        files={"pdf": open(pdf_path, "rb")},
        data={"user_data": '{"name": "Test User"}'}
    )
    
    assert response.status_code == 200
    result = response.json()
    
    # Verify output in S3
    output_key = result["filled_pdf_path"]
    obj = s3_client.head_object(Bucket="pdf-autofiller-prod", Key=output_key)
    assert obj["ContentLength"] > 0
```

---

## 📊 Deployment Checklist

### Phase 2: Docker (Universal Image)
- [ ] Create unified Dockerfile
- [ ] Build image locally
- [ ] Test with `SOURCE_TYPE=local`
- [ ] Test with `SOURCE_TYPE=aws` (local AWS creds)
- [ ] Run module tests inside container
- [ ] Optimize image size (<500MB)
- [ ] Document environment variables

### Phase 3: AWS Lambda
- [ ] Create ECR repository
- [ ] Create S3 buckets
- [ ] Create IAM roles and policies
- [ ] Store API keys in Secrets Manager
- [ ] Create Lambda function (Docker)
- [ ] Configure API Gateway
- [ ] Set environment variables
- [ ] Deploy Docker image to Lambda
- [ ] Test health endpoint
- [ ] Test mapping endpoint
- [ ] Monitor CloudWatch logs

### Phase 4: SDK Setup
- [ ] Verify Lambda deployment
- [ ] Configure SDK with API Gateway URL
- [ ] Test SDK CLI
- [ ] Test SDK Python API
- [ ] Document SDK usage with deployed API

### Phase 5: Integration Testing
- [ ] Create integration test suite
- [ ] Test module locally
- [ ] Test module in Docker
- [ ] Test module in Lambda
- [ ] Test SDK → Lambda → S3 flow
- [ ] Verify outputs in S3
- [ ] Test error handling
- [ ] Test caching behavior

---

## 🔄 Reusability Strategy

### Same Docker Image for Multiple Platforms

**Key Decision**: ✅ **YES, use one Docker image for all platforms**

**How**:

1. **Build once**:
   ```bash
   docker build -t pdf-mapper:universal -f deployment/docker/Dockerfile .
   ```

2. **Deploy to AWS Lambda**:
   ```bash
   docker tag pdf-mapper:universal $AWS_ECR/pdf-mapper:latest
   docker push $AWS_ECR/pdf-mapper:latest
   aws lambda update-function-code --function-name pdf-mapper --image-uri $AWS_ECR/pdf-mapper:latest
   ```

3. **Deploy to Azure Functions** (same image!):
   ```bash
   docker tag pdf-mapper:universal $AZURE_ACR/pdf-mapper:latest
   docker push $AZURE_ACR/pdf-mapper:latest
   az functionapp config container set --name pdf-mapper --image $AZURE_ACR/pdf-mapper:latest
   ```

4. **Deploy to GCP Cloud Run** (same image!):
   ```bash
   docker tag pdf-mapper:universal gcr.io/$PROJECT/pdf-mapper:latest
   docker push gcr.io/$PROJECT/pdf-mapper:latest
   gcloud run deploy pdf-mapper --image gcr.io/$PROJECT/pdf-mapper:latest
   ```

**Configuration per platform**:
- AWS: `SOURCE_TYPE=aws`, S3 paths in env vars
- Azure: `SOURCE_TYPE=azure`, Blob paths in env vars
- GCP: `SOURCE_TYPE=gcp`, GCS paths in env vars

**Benefits**:
- ✅ Test once, deploy anywhere
- ✅ Single CI/CD pipeline
- ✅ Consistent behavior across clouds
- ✅ Easy to switch platforms

---

## 🎯 Next Steps (Recommended Order)

1. **Create universal Dockerfile** ← START HERE
2. **Test Docker locally with all sources**
3. **Create AWS deployment scripts**
4. **Deploy to AWS Lambda**
5. **Verify with integration tests**
6. **Configure SDK to use Lambda endpoint**
7. **Run E2E tests**
8. **Document deployment process**
9. **Create Azure/GCP deployment scripts** (use same Docker image!)

---

## 📝 Notes

- **EC2 Alternative**: Same Docker image can run on EC2 with docker-compose
- **Cost Optimization**: Lambda only charges for execution time
- **Scalability**: Lambda auto-scales, EC2 needs manual scaling
- **Cold Starts**: Lambda ~2-3s, EC2 always warm
- **Recommendation**: Start with Lambda for mapper, use EC2 for chatbot (long-running)

