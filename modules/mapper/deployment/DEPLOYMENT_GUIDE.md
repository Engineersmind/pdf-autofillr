# Mapper Module — Deployment Guide

**Module:** `modules/mapper`
**Architecture:** Download → Process → Upload (compute-agnostic, storage-agnostic)
**Compute options:** Docker/local, AWS Lambda, Azure Functions, GCP Cloud Functions
**Storage options:** local filesystem, AWS S3, Azure Blob (planned), GCP GCS (planned)

---

## How the pipeline works (platform-independent)

Every operation follows the same pattern regardless of where it runs:

```
1. create_job_context()     → UUID-scoped /tmp/processing/<uuid>/ dir
2. download_file()          → pull input files to local temp dir
3. operations.py            → process entirely in temp dir (Java JAR + LLM)
4. upload_file()            → push outputs to destination storage
5. cleanup_processing_dir() → always in try/finally
```

`operations.py` has zero knowledge of storage. The only thing that changes per platform is:
- Which entrypoint file is the handler (`aws_lambda.py` / `http_server.py` / etc.)
- The `config.ini [general] source_type` value
- Environment variables (credentials, API keys)

---

## Platform Matrix

| Platform | Status | Storage | Java JRE | Ephemeral | Concurrency safe |
|----------|--------|---------|----------|-----------|-----------------|
| Docker (HTTP) | ✅ Ready | local / AWS | included | unlimited | ✅ UUID dirs |
| AWS Lambda | ✅ Ready | AWS S3 | ✅ layer | /tmp 10 GB | ✅ UUID dirs |
| Azure Functions | ⚠️ Backend TBD | Azure Blob | custom layer | /tmp varies | ✅ UUID dirs |
| GCP Cloud Functions | ⚠️ Backend TBD | GCS | custom layer | /tmp 512 MB–8 GB | ✅ UUID dirs |
| Local / CLI | ✅ Ready | local | system JRE | filesystem | single user |

---

## 1. Docker / Local HTTP Server

**Status:** Production-ready.

### Build & run

```bash
# From repo root
docker build -t pdf-autofiller-mapper -f modules/mapper/deployment/docker/Dockerfile .

# Local storage (mount your data directory)
docker run -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e ANTHROPIC_API_KEY=sk-... \
  pdf-autofiller-mapper

# AWS S3 storage
docker run -p 8000:8000 \
  -e AWS_ACCESS_KEY_ID=... \
  -e AWS_SECRET_ACCESS_KEY=... \
  -e AWS_DEFAULT_REGION=us-east-1 \
  -e ANTHROPIC_API_KEY=sk-... \
  pdf-autofiller-mapper
```

### config.ini for Docker + local storage

```ini
[general]
source_type = local

[local]
input_base_path = /app/data/modules/mapper_sample/input/
output_base_path = /app/data/modules/mapper_sample/output
processing_dir = /tmp/processing
```

### config.ini for Docker + S3 storage

```ini
[general]
source_type = aws

[aws]
output_base_path = s3://your-bucket/pdf-autofiller
cache_registry_path = s3://your-bucket/pdf-autofiller/cache/hash_registry.json
```

### Considerations

- **JRE:** Already included in the Dockerfile (`default-jre`). The Java JAR for embed/fill stages works out of the box.
- **Concurrency:** HTTP server runs multiple workers. UUID-scoped temp dirs prevent collision between simultaneous requests.
- **Scaling:** Use Docker Compose or Kubernetes for horizontal scaling. No shared state in `/tmp` between containers.
- **Health check:** `GET /health` is wired to the Docker `HEALTHCHECK` directive. Load balancers should use this.
- **Memory:** LLM calls + PDF processing can peak at 1–2 GB per worker. Set container memory limits accordingly.

---

## 2. AWS Lambda

**Status:** Production-ready.

### Package the function

Lambda cannot use the Docker image directly if you want the lightweight zip deployment. Two options:

**Option A — Container Image (recommended for JRE requirement)**

```dockerfile
# Use the existing Dockerfile but change the CMD
# Add to Dockerfile or override in lambda.Dockerfile:
FROM public.ecr.aws/lambda/python:3.11

# Install JRE (needed for embed/fill operations)
RUN dnf install -y java-17-amazon-corretto-headless && dnf clean all

COPY modules/mapper/requirements.txt .
RUN pip install -r requirements.txt

COPY modules/mapper/ /var/task/
COPY modules/mapper/config.ini /var/task/config.ini

CMD ["entrypoints.aws_lambda.lambda_handler"]
```

```bash
# Build and push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
docker build -t pdf-autofiller-lambda -f lambda.Dockerfile .
docker tag pdf-autofiller-lambda <account>.dkr.ecr.<region>.amazonaws.com/pdf-autofiller-mapper:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/pdf-autofiller-mapper:latest
```

**Option B — Zip deployment with Lambda Layer for JRE**

Only viable if you use an Amazon Linux 2 JRE layer. Most teams prefer Option A.

### Lambda configuration

| Setting | Value |
|---------|-------|
| Handler | `entrypoints.aws_lambda.lambda_handler` |
| Runtime | Python 3.11 (or container image) |
| Timeout | 900 seconds (15 min max) — run_all takes 3–8 min |
| Memory | 3008 MB recommended (LLM + PDF processing) |
| Ephemeral storage | 10240 MB (10 GB) — set this, PDFs can be large |
| Architecture | x86_64 (arm64 needs JRE layer adjustment) |

### Environment variables for Lambda

```
# LLM (choose one)
ANTHROPIC_API_KEY=sk-...         # Direct Claude
OPENAI_API_KEY=sk-...            # OpenAI / GPT
# For Bedrock: IAM role is sufficient, no key needed

# AWS credentials (not needed if using IAM role — preferred)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1

# App token (Lambda checks X-API-Key header)
MAPPER_LAMBDA_API_TOKEN=your-secret-token

# Backend API (for fetching S3 document URLs)
BACKEND_API_URL=https://your-backend/api
BACKEND_API_KEY=...

# Optional: Teams notifications
TEAMS_WEBHOOK_URL=https://...
```

### config.ini for Lambda

```ini
[general]
source_type = aws

[aws]
output_base_path = s3://your-bucket/pdf-autofiller
cache_registry_path = s3://your-bucket/pdf-autofiller/cache/hash_registry.json
global_input_json_s3_uri = s3://your-bucket/global_input_keys.json
rag_bucket_name = rag-bucket-pdf-filler

[mapping]
llm_model = bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0
# or: llm_model = claude-3-5-sonnet-20241022
```

### IAM permissions needed

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:HeadObject"],
      "Resource": "arn:aws:s3:::your-bucket/*"
    },
    {
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel"],
      "Resource": "*"
    }
  ]
}
```

### Considerations

- **Cold start:** Container images have 5–15 s cold start. Use provisioned concurrency for latency-sensitive operations (`check_embed_file`).
- **JRE cold start:** Java subprocess startup adds ~2–3 s on first embed/fill call in a cold container. Warm containers reuse the JVM process.
- **Warm containers reuse `/tmp`:** UUID dirs per `JobContext` prevent state leakage between warm invocations. Cache registry download is still needed each invocation (S3 is the source of truth).
- **Function URL vs API Gateway:** The entrypoint already handles the Lambda Function URL body parsing (`event['body']` string → JSON). API Gateway v2 uses the same format.
- **`run_all` timeout:** For large PDFs with `use_second_mapper = true`, plan for 10–12 min. Lambda max is 15 min. For very large PDFs, consider splitting into separate Lambda invocations per stage.

---

## 3. Azure Functions

**Status:** Storage backend not yet implemented (`AzureStorageConfig.download_file` raises `NotImplementedError`).

### What's already in place

- `entrypoints/azure_function.py` — thin HTTP wrapper (reads request body, routes to `route_operation`)
- `config.ini [azure]` section — paths configured
- Factory fails fast with a clear error if `source_type = azure` before backend is ready

### To make it production-ready

**Step 1 — Implement `AzureStorageConfig`** (`src/configs/azure.py`):

```python
def download_file(self, source_path: str, local_path: str) -> str:
    # source_path format: azure://container/blob/path
    container, blob_path = self._parse_azure_path(source_path)
    client = BlobServiceClient.from_connection_string(os.getenv('AZURE_STORAGE_CONNECTION_STRING'))
    blob_client = client.get_blob_client(container=container, blob=blob_path)
    with open(local_path, 'wb') as f:
        f.write(blob_client.download_blob().readall())
    return local_path

def upload_file(self, local_path: str, destination_path: str) -> str:
    container, blob_path = self._parse_azure_path(destination_path)
    client = BlobServiceClient.from_connection_string(os.getenv('AZURE_STORAGE_CONNECTION_STRING'))
    with open(local_path, 'rb') as f:
        client.get_blob_client(container=container, blob=blob_path).upload_blob(f, overwrite=True)
    return destination_path
```

**Step 2 — Add `azure-storage-blob` to requirements:**

```
azure-storage-blob>=12.0.0
```

**Step 3 — Add to `_IMPLEMENTED` set in `factory.py`:**

```python
_IMPLEMENTED = {'aws', 'local', 'azure'}
```

**Step 4 — Add auth to `entrypoints/azure_function.py`** (currently has `# TODO`):

```python
# Use Azure Function key (host key or function key) from headers
# x-functions-key header is validated by the Azure runtime if auth level = function
```

### Azure Function configuration

```
# function.json (HTTP trigger)
{
  "bindings": [{
    "type": "httpTrigger",
    "authLevel": "function",
    "methods": ["POST"],
    "name": "req"
  }, ...]
}
```

| Setting | Value |
|---------|-------|
| Plan | Premium EP1 or Dedicated (Consumption has 230 s timeout — too short) |
| OS | Linux |
| Python version | 3.11 |
| Timeout | 10 min (Premium), unlimited (Dedicated) |
| Temp storage | /tmp — limited on Consumption, use Premium for large PDFs |

### JRE on Azure Functions

Azure Functions Linux containers do not include JRE. Options:
1. **Custom Docker image** — extend the base image, `apt-get install default-jre`
2. **Startup script** — `apt-get install` in a startup script (slow, not recommended for prod)
3. **Avoid Java in Azure** — use the Python-based filler if available as fallback

### config.ini for Azure

```ini
[general]
source_type = azure

[azure]
output_base_path = azure://your-container/pdf-autofiller
cache_registry_path = azure://your-container/pdf-autofiller/cache/hash_registry.json
global_input_json_uri = azure://your-container/global_input_keys.json
```

### Environment variables

```
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
OPENAI_API_KEY=sk-...         # or AZURE_OPENAI_API_KEY for Azure OpenAI
AZURE_API_BASE=https://...    # if using Azure OpenAI
```

---

## 4. GCP Cloud Functions

**Status:** Storage backend not yet implemented (`GCPStorageConfig.download_file` raises `NotImplementedError`).

### What's already in place

- `entrypoints/gcp_function.py` — thin HTTP wrapper
- `config.ini [gcp]` section — paths configured
- Factory fails fast with `NotImplementedError` before any pipeline work

### To make it production-ready

**Step 1 — Implement `GCPStorageConfig`** (`src/configs/gcp.py`):

```python
def download_file(self, source_path: str, local_path: str) -> str:
    # source_path format: gs://bucket/path
    bucket_name, blob_name = self._parse_gcs_path(source_path)
    from google.cloud import storage
    client = storage.Client()
    client.bucket(bucket_name).blob(blob_name).download_to_filename(local_path)
    return local_path

def upload_file(self, local_path: str, destination_path: str) -> str:
    bucket_name, blob_name = self._parse_gcs_path(destination_path)
    from google.cloud import storage
    client = storage.Client()
    client.bucket(bucket_name).blob(blob_name).upload_from_filename(local_path)
    return destination_path
```

**Step 2 — Add `google-cloud-storage` to requirements.**

**Step 3 — Add to `_IMPLEMENTED` in `factory.py`:**

```python
_IMPLEMENTED = {'aws', 'local', 'gcp'}
```

### GCP Cloud Functions configuration

| Setting | Value |
|---------|-------|
| Gen | 2nd gen (Cloud Run-backed, no 9 min timeout) |
| Runtime | python311 |
| Memory | 4 GiB |
| Timeout | 3600 s (2nd gen max) |
| Ephemeral storage | 512 MB default, configurable up to 10 GB (2nd gen) |
| Entry point | `mapper_handler` (in `entrypoints/gcp_function.py`) |

### JRE on GCP Cloud Functions

2nd gen Cloud Functions run on Cloud Run containers. JRE options:
1. **Custom container** — recommended. Build from `python:3.11-slim`, add JRE, deploy as Cloud Run service.
2. **Buildpacks** — limited, harder to add JRE
3. **Cloud Run directly** — use the Docker image from section 1 (`CMD` override to GCP handler)

### config.ini for GCP

```ini
[general]
source_type = gcp

[gcp]
output_base_path = gs://your-bucket/pdf-autofiller
cache_registry_path = gs://your-bucket/pdf-autofiller/cache/hash_registry.json
global_input_json_uri = gs://your-bucket/global_input_keys.json
```

### Environment variables

```
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
# Or use Workload Identity (no key file needed on GCP infra)
GOOGLE_CLOUD_PROJECT=your-project-id
ANTHROPIC_API_KEY=sk-...   # or use Vertex AI model
```

For Vertex AI LLM:

```ini
[mapping]
llm_model = vertex_ai/claude-3-5-sonnet@20241022
```

---

## 5. config.ini Cheat Sheet

One file change is all that's needed to switch platforms:

| Scenario | `source_type` | Key settings |
|----------|--------------|-------------|
| Local dev | `local` | `input_base_path`, `output_base_path` pointing to local dirs |
| Docker + local data | `local` | Same, but `/app/data/...` paths |
| Docker + S3 | `aws` | `output_base_path = s3://...` |
| Lambda (prod) | `aws` | `output_base_path = s3://...`, use IAM role |
| Azure Functions | `azure` | `output_base_path = azure://...` |
| GCP Cloud Functions | `gcp` | `output_base_path = gs://...` |

LLM is independent of storage. Mix any combination:

```ini
[mapping]
llm_model = bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0  # AWS Bedrock
# llm_model = claude-3-5-sonnet-20241022                        # Direct Anthropic
# llm_model = gpt-4o                                            # OpenAI
# llm_model = azure/gpt-4                                       # Azure OpenAI
# llm_model = vertex_ai/gemini-pro                             # Google Vertex
```

---

## 6. Java JAR — Platform Considerations

The embed and fill stages call `form_field_filler-1.0.0-jar-with-dependencies.jar` as a subprocess. This is the one platform constraint.

| Platform | JRE status | Solution |
|----------|-----------|----------|
| Docker | ✅ Included (`default-jre` in Dockerfile) | Nothing to do |
| AWS Lambda (container) | ✅ Add to lambda.Dockerfile | `dnf install java-17-amazon-corretto-headless` |
| AWS Lambda (zip) | ⚠️ Lambda Layer needed | Package JRE in a Lambda Layer |
| Azure Functions | ⚠️ Custom container needed | Extend base image |
| GCP Cloud Functions (2nd gen) | ⚠️ Custom container (Cloud Run) | Use Docker image directly |
| Local / CI | ✅ System JRE | `apt install default-jre` or brew |

**Verifying JRE at startup:**

```python
import subprocess
result = subprocess.run(['java', '-version'], capture_output=True)
if result.returncode != 0:
    raise RuntimeError("Java not found — embed/fill operations require JRE")
```

Consider adding this check to `entrypoints/http_server.py` startup or a health endpoint.

---

## 7. Ephemeral Storage Sizing

Processing happens in `/tmp/processing/<uuid>/`. Files accumulated per operation:

| Stage | Files | Typical size |
|-------|-------|-------------|
| extract | input PDF + extracted JSON | 5–50 MB |
| map | + mapped JSON, radio groups | +1–2 MB |
| embed | + embedded PDF | +5–50 MB |
| fill | + filled PDF | +5–50 MB |
| run_all | all of the above | 20–150 MB |

Recommended ephemeral storage per platform:
- **Lambda:** Set to 2048 MB minimum, 10240 MB for large PDFs
- **GCP 2nd gen:** Default 512 MB is tight. Set to 2–4 GB
- **Docker:** `/tmp` is backed by host RAM by default. Override with `--tmpfs /tmp:size=4g`
- **Azure Premium:** 21 GB SSD temporary storage per instance

Each UUID dir is cleaned up in `finally`. Peak usage is one dir per concurrent request.

---

## 8. Adding a New Compute Platform

The entrypoint pattern is consistent. To add a new platform (e.g., Render, Railway, Modal):

1. Create `entrypoints/new_platform.py`
2. Parse the platform's event/request format
3. Call `create_job_context(get_file_config(), user_id, session_id, pdf_doc_id)`
4. Download inputs: `ctx.download_file(ctx.source_input_pdf, ctx.local_input_pdf)`
5. Call the appropriate `handle_*_operation` from `src/handlers/operations.py`
6. Wrap in `try/finally` with `cleanup_processing_directory(ctx.processing_dir)`
7. Return the platform's response format

The operations layer never changes. Total new code per platform: ~80–120 lines.

---

## 9. Adding a New Storage Backend

1. Create `src/configs/minio.py` (or s3-compatible, sftp, etc.) implementing:
   - `download_file(source_path, local_path) -> str`
   - `upload_file(local_path, destination_path) -> str`
   - `file_exists(path) -> bool`
2. Add to `_BACKEND_CLASSES` in `src/storage/backends/factory.py`
3. Add to `_IMPLEMENTED` set
4. Add credential check to `_CREDENTIAL_CHECKS` if applicable
5. Add a `[minio]` section to `config.ini`
6. Set `source_type = minio` in `[general]`

Zero changes to operations, handlers, or entrypoints.
