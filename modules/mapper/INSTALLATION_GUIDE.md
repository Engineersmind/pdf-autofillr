# Mapper Module - Installation Guide

## 📋 Quick Reference

### Option 1: Core Only (No Cloud - For Local Testing)
```bash
pip install -r requirements.txt
```

### Option 2: With AWS Support (Current Setup)
```bash
pip install -r requirements-aws.txt
```

### Option 3: With Azure Support
```bash
pip install -r requirements-azure.txt
```

### Option 4: With GCP Support
```bash
pip install -r requirements-gcp.txt
```

### Option 5: Multi-Cloud (All Platforms)
```bash
pip install -r requirements-aws.txt -r requirements-azure.txt -r requirements-gcp.txt
```

---

## 🔍 What's in Each Requirements File?

### `requirements.txt` - Core Dependencies (Platform-Agnostic)
**Size**: ~20 packages  
**Cloud SDKs**: ❌ None  
**Use Case**: Local development, testing, CLI usage

Includes:
- PyMuPDF (PDF processing)
- OpenAI SDK (LLM)
- Pydantic (data validation)
- httpx, aiohttp (HTTP clients)
- tenacity (retry logic)

### `requirements-aws.txt` - AWS-Specific
**Size**: ~24 packages (core + AWS)  
**Cloud SDKs**: ✅ boto3, botocore, s3transfer  
**Use Case**: AWS Lambda deployment

Includes everything in `requirements.txt` PLUS:
- boto3 (AWS SDK)
- botocore (AWS core)
- s3transfer (S3 operations)

### `requirements-azure.txt` - Azure-Specific
**Size**: ~23 packages (core + Azure)  
**Cloud SDKs**: ✅ azure-storage-blob, azure-identity  
**Use Case**: Azure Functions deployment

Includes everything in `requirements.txt` PLUS:
- azure-storage-blob (Blob Storage)
- azure-identity (Authentication)
- azure-functions (Functions runtime)

### `requirements-gcp.txt` - GCP-Specific
**Size**: ~23 packages (core + GCP)  
**Cloud SDKs**: ✅ google-cloud-storage  
**Use Case**: Google Cloud Functions deployment

Includes everything in `requirements.txt` PLUS:
- google-cloud-storage (GCS)
- google-cloud-logging (Logging)
- functions-framework (Functions runtime)

---

## 📦 Installation Steps

### For Your Current Repository (AWS)

1. **Navigate to mapper module**:
   ```bash
   cd modules/mapper
   ```

2. **Install AWS dependencies**:
   ```bash
   pip install -r requirements-aws.txt
   ```

3. **Verify installation**:
   ```bash
   python -c "import boto3; import pymupdf; import openai; print('✅ All dependencies installed!')"
   ```

---

## 🧪 Testing Different Platforms

### Test Core Logic (No Cloud)
```bash
pip install -r requirements.txt
pytest tests/test_core.py
```

### Test with AWS
```bash
pip install -r requirements-aws.txt
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
pytest tests/test_aws_integration.py
```

### Test with Azure
```bash
pip install -r requirements-azure.txt
export AZURE_STORAGE_CONNECTION_STRING=test
pytest tests/test_azure_integration.py
```

---

## 🚀 Deployment Examples

### Deploy to AWS Lambda
```bash
# Install AWS dependencies
pip install -r requirements-aws.txt -t ./package

# Copy source code
cp -r src/ package/

# Copy AWS entry point
cp entrypoints/aws_lambda.py package/lambda_handler.py

# Create deployment package
cd package && zip -r ../mapper-aws.zip . && cd ..

# Deploy
aws lambda update-function-code \
  --function-name pdf-mapper \
  --zip-file fileb://mapper-aws.zip
```

### Deploy to Azure Functions
```bash
# Install Azure dependencies
pip install -r requirements-azure.txt -t .python_packages/lib/site-packages

# Copy entry point
cp entrypoints/azure_function.py __init__.py

# Deploy
func azure functionapp publish pdf-mapper-app
```

---

## 💡 Why Separate Requirements?

1. **Smaller Builds**: Only install what you need
   - Core: ~50MB
   - Core + AWS: ~80MB
   - Core + All Clouds: ~150MB

2. **Faster Deployments**: Less time to upload packages

3. **Better Testing**: Test core logic without cloud mocks

4. **Clear Dependencies**: Know exactly what each platform needs

5. **No Conflicts**: Avoid version conflicts between cloud SDKs

---

## ✅ Verification Commands

```bash
# Check what's installed
pip list

# Check package sizes
pip list --format=columns | grep -E 'boto3|azure|google-cloud'

# Check for cloud dependencies in core
grep -r "import boto3" src/  # Should return nothing!
grep -r "import azure" src/   # Should return nothing!
grep -r "from google.cloud" src/  # Should return nothing!
```

---

## 🔧 Troubleshooting

### Issue: "Module not found: boto3"
**Solution**: You're using AWS entry point but installed core only
```bash
pip install -r requirements-aws.txt
```

### Issue: "Too many dependencies in Lambda"
**Solution**: Use Lambda Layer for common dependencies
```bash
# Create layer with core dependencies
pip install -r requirements.txt -t python/
zip -r layer.zip python/
```

### Issue: "Conflict between boto3 versions"
**Solution**: Use exact versions from requirements-aws.txt
```bash
pip install --force-reinstall -r requirements-aws.txt
```
