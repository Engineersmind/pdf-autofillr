# Docker Strategy - Module-Based Approach

## 🎯 Strategy Overview

### **One Docker Image PER MODULE** (Not per cloud)

```
┌─────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT STRUCTURE                      │
└─────────────────────────────────────────────────────────────┘

modules/mapper/
├── Dockerfile               ← Mapper-specific image
├── requirements.txt         ← ALL dependencies (AWS+Azure+GCP)
└── src/

modules/chatbot/
├── Dockerfile               ← Chatbot-specific image
├── requirements.txt         ← ALL dependencies (AWS+Azure+GCP)
└── src/

modules/rag/
├── Dockerfile               ← RAG-specific image
├── requirements.txt         ← ALL dependencies (AWS+Azure+GCP)
└── src/

modules/orchestrator/
├── Dockerfile               ← Orchestrator-specific image
├── requirements.txt         ← ALL dependencies (AWS+Azure+GCP)
└── src/
```

**Each image can deploy to ANY cloud via environment variables**

---

## 📦 Requirements Strategy

### Option A: Separate Files (Current - More Complex)

```
modules/mapper/
├── requirements.txt          # Core
├── requirements-aws.txt      # + AWS
├── requirements-azure.txt    # + Azure
├── requirements-gcp.txt      # + GCP
└── requirements-api.txt      # + API
```

**Dockerfile**:
```dockerfile
# Install all requirements (verbose)
RUN pip install -r requirements.txt \
    && pip install -r requirements-api.txt \
    && pip install -r requirements-aws.txt \
    && pip install -r requirements-azure.txt \
    && pip install -r requirements-gcp.txt
```

**Maintenance**: 5 files to update ❌

---

### Option B: Single File (Recommended - Simple)

```
modules/mapper/
└── requirements.txt          # Everything!
```

**Dockerfile**:
```dockerfile
# Install all requirements (clean!)
RUN pip install -r requirements.txt
```

**Maintenance**: 1 file to update ✅

---

## 📊 Size Comparison

### Image Sizes:

| Approach | Base | Core | AWS | Azure | GCP | Total |
|----------|------|------|-----|-------|-----|-------|
| **Minimal** | 150MB | 400MB | - | - | - | **550MB** |
| **Single Cloud** | 150MB | 400MB | 50MB | - | - | **600MB** |
| **All Clouds** | 150MB | 400MB | 50MB | 80MB | 70MB | **750MB** |

**Extra cost for "All Clouds": Only 150MB!** (~20% increase)

**Benefits of including all clouds**:
- ✅ Switch clouds without rebuild
- ✅ Test locally with any source
- ✅ Simpler CI/CD (one build)
- ✅ Same image for dev/staging/prod

---

## 🏗️ Recommended Structure

### Final Directory Structure:

```
pdf-autofillr/
├── modules/
│   ├── mapper/
│   │   ├── Dockerfile                    ← Mapper Docker
│   │   ├── requirements.txt              ← ALL dependencies
│   │   ├── src/
│   │   └── api_server.py
│   │
│   ├── chatbot/
│   │   ├── Dockerfile                    ← Chatbot Docker
│   │   ├── requirements.txt              ← ALL dependencies (different from mapper)
│   │   └── src/
│   │
│   ├── rag/
│   │   ├── Dockerfile                    ← RAG Docker
│   │   ├── requirements.txt              ← ALL dependencies
│   │   └── src/
│   │
│   └── orchestrator/
│       ├── Dockerfile                    ← Orchestrator Docker
│       ├── requirements.txt              ← ALL dependencies
│       └── src/
│
└── deployment/
    ├── aws/
    │   ├── mapper/
    │   │   └── deploy.sh                 ← Deploy mapper to AWS
    │   ├── chatbot/
    │   │   └── deploy.sh                 ← Deploy chatbot to AWS
    │   └── ...
    │
    ├── azure/
    │   ├── mapper/
    │   │   └── deploy.sh                 ← Deploy mapper to Azure
    │   └── ...
    │
    └── docker/                           ← Deprecated (move to modules)
        └── ...
```

---

## 🔄 Proposed Changes

### 1. **Consolidate Requirements** (Mapper Module)

**Current**: 5 files
- requirements.txt
- requirements-aws.txt
- requirements-azure.txt
- requirements-gcp.txt
- requirements-api.txt

**Proposed**: 1 file
- requirements.txt (includes everything)

**Benefits**:
- ✅ Easier to maintain
- ✅ Simpler Dockerfile
- ✅ No conditional logic
- ✅ Clear dependencies

---

### 2. **Move Dockerfile to Module** (Co-locate with code)

**Current**:
```
deployment/docker/mapper/Dockerfile    ← Far from code
modules/mapper/src/                    ← Code here
```

**Proposed**:
```
modules/mapper/Dockerfile              ← Next to code
modules/mapper/src/                    ← Code here
```

**Benefits**:
- ✅ Self-contained module
- ✅ Easier to find
- ✅ Module-specific builds
- ✅ Independent versioning

---

### 3. **Keep Deployment Scripts Separate** (Cloud-specific)

**Keep in deployment/**:
```
deployment/
├── aws/mapper/deploy.sh               ← AWS-specific deployment
├── azure/mapper/deploy.sh             ← Azure-specific deployment
└── gcp/mapper/deploy.sh               ← GCP-specific deployment
```

**Why separate?**
- Deployment scripts are cloud-specific (IAM, permissions, etc.)
- Docker image is cloud-agnostic
- Clear separation of concerns

---

## 🎯 Implementation Plan

### Phase 1: Consolidate Mapper Requirements ✅

1. Merge all requirements into single file
2. Update Dockerfile to use single requirements.txt
3. Test locally
4. Commit changes

### Phase 2: Move Dockerfile to Module ✅

1. Move `deployment/docker/mapper/Dockerfile` → `modules/mapper/Dockerfile`
2. Update paths in Dockerfile
3. Test build
4. Update documentation

### Phase 3: Create Deployment Scripts per Cloud

1. Keep deployment scripts in `deployment/{cloud}/mapper/`
2. Each script references `modules/mapper/Dockerfile`
3. Cloud-specific configuration

### Phase 4: Repeat for Other Modules

1. Apply same pattern to chatbot, rag, orchestrator
2. Each module self-contained with Dockerfile
3. Deployment scripts reference module Dockerfiles

---

## 🚀 Example: Mapper Module

### Structure:
```
modules/mapper/
├── Dockerfile               ← Universal image (all clouds)
├── requirements.txt         ← Single consolidated file
├── .dockerignore           ← Exclude unnecessary files
├── src/
├── tests/
└── api_server.py
```

### Requirements.txt (Consolidated):
```txt
# Core Dependencies
PyMuPDF==1.26.5
numpy==2.3.5

# LLM
openai==2.6.0
anthropic>=0.18.0

# Cloud SDKs (ALL included)
boto3>=1.40.0                # AWS
azure-storage-blob>=12.19.0  # Azure
google-cloud-storage>=2.14.0 # GCP

# API
fastapi>=0.109.0
uvicorn[standard]>=0.27.0

# ... rest of dependencies
```

### Dockerfile (Simplified):
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy and install requirements (one command!)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY api_server.py .

# Runtime configuration via env vars
ENV SOURCE_TYPE=local

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0"]
```

### Build:
```bash
# From repo root
docker build -t pdf-mapper:latest -f modules/mapper/Dockerfile modules/mapper/

# Or from module directory
cd modules/mapper
docker build -t pdf-mapper:latest .
```

### Deploy to AWS:
```bash
cd deployment/aws/mapper
./deploy.sh
# Script builds modules/mapper/Dockerfile and pushes to ECR
```

### Deploy to Azure:
```bash
cd deployment/azure/mapper
./deploy.sh
# Same Docker image, different deployment
```

---

## ❓ Your Questions Answered

### Q1: Should each module have different Docker?
**A: YES!** ✅ 
- `modules/mapper/Dockerfile`
- `modules/chatbot/Dockerfile`
- `modules/rag/Dockerfile`

### Q2: Put all cloud SDKs in single requirements?
**A: YES!** ✅ Much easier!
- One `requirements.txt` with everything
- ~200MB extra for all clouds (negligible)
- Maximum flexibility

### Q3: What about deployment scripts?
**A: Keep separate per cloud** ✅
- `deployment/aws/mapper/deploy.sh`
- `deployment/azure/mapper/deploy.sh`
- Scripts reference module's Dockerfile

---

## 🎯 Summary

### ✅ DO:
- One Docker image per module (mapper, chatbot, rag)
- Include ALL cloud SDKs in single requirements.txt
- Put Dockerfile in module directory (`modules/mapper/Dockerfile`)
- Keep deployment scripts in `deployment/{cloud}/mapper/`

### ❌ DON'T:
- Separate Docker images per cloud (unnecessary complexity)
- Separate requirements files (harder to maintain)
- Put Dockerfile far from code

### 🎁 Benefits:
- ✅ Simple to build: `docker build -f modules/mapper/Dockerfile .`
- ✅ Simple to deploy: Same image → AWS/Azure/GCP
- ✅ Simple to maintain: One requirements file
- ✅ Maximum flexibility: Configure at runtime

---

## 🚀 Ready to Implement?

Let me know if you want me to:
1. ✅ Consolidate requirements files into one
2. ✅ Move Dockerfile to module directory
3. ✅ Update deployment scripts
4. ✅ Test the new structure

Your call! 🎯
