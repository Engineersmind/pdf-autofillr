# rag-lambda — Terraform Infrastructure

Full infrastructure-as-code for the RAG PDF-Filler Lambda. Covers AWS (primary), Azure, GCP, and local Docker.

---

## Directory Structure

```
terraform/rag-lambda/
├── main.tf                        # Root: wires all modules together
├── variables.tf                   # All input variables (derived from settings.py + .env)
├── outputs.tf                     # Key resource identifiers
├── .gitignore
│
├── modules/
│   ├── aws/                       # PRIMARY — Lambda, ECR, S3 ×2, IAM, API GW, CloudWatch
│   ├── azure/                     # OPTIONAL — Blob Storage, Key Vault, ACR, App Insights
│   ├── gcp/                       # OPTIONAL — Cloud Storage, Secret Manager, Artifact Registry
│   └── local/                     # DEV ONLY — generates .env.local + docker-compose.local.yml
│
├── environments/
│   ├── dev/terraform.tfvars
│   ├── staging/terraform.tfvars
│   └── prod/terraform.tfvars
│
└── scripts/
    ├── bootstrap_backend.sh       # One-time: create S3 state bucket + DynamoDB lock table
    ├── constructor.sh             # Provision all infra for an environment
    ├── destructor.sh              # Tear down all infra for an environment
    ├── build_and_push.sh          # Build Docker image → push to ECR → update Lambda
    └── logging.sh                 # Tail logs, view metrics, pull S3 session logs
```

---

## Quick Start

### 1. Prerequisites

```bash
# Required tools
terraform >= 1.6
aws-cli >= 2.x      (configured with your IAM credentials)
docker              (buildx with linux/amd64 support)
jq
```

### 2. Bootstrap remote state (once per AWS account)

```bash
chmod +x scripts/*.sh
./scripts/bootstrap_backend.sh ap-south-1
```

### 3. Export secrets

**Never put secrets in tfvars files.** Use environment variables:

```bash
export TF_VAR_openai_api_key="sk-proj-..."
export TF_VAR_x_api_key="7KmP@9xQ2NvL5!"
export TF_VAR_teams_webhook_url="https://defaultb3869958a2da40b3a9a11713bbdc23..."
export TF_VAR_backend_auth_token="your_backend_secret"   # optional
```

### 4. Provision infrastructure

```bash
./scripts/constructor.sh dev
```

### 5. Build & push the Lambda image

```bash
./scripts/build_and_push.sh dev
```

### 6. Apply again to wire the real image URI

```bash
# Edit environments/dev/terraform.tfvars — set ecr_image_uri to the output from step 5
./scripts/constructor.sh dev
```

---

## Environment Variables Mapped

All variables are derived from `config/settings.py` and `.env`:

| Terraform variable            | Lambda env var                | Source file        |
|-------------------------------|-------------------------------|--------------------|
| `rag_bucket_name`             | `S3_BUCKET`                   | settings.py        |
| `prod_bucket_name`            | `PROD_BUCKET`                 | settings.py        |
| `lambda_function_name`        | `RAG_LAMBDA_FUNCTION_NAME`    | settings.py        |
| `openai_api_key`              | `OPENAI_API_KEY`              | .env (secret)      |
| `x_api_key`                   | `X_API_KEY`                   | .env (secret)      |
| `teams_webhook_url`           | `TEAMS_WEBHOOK_URL`           | .env (secret)      |
| `gpt4_model`                  | `GPT4_MODEL`                  | settings.py        |
| `gpt4_temperature`            | `GPT4_TEMPERATURE`            | settings.py        |
| `gpt4_max_tokens`             | `GPT4_MAX_TOKENS`             | settings.py        |
| `embedding_model`             | `EMBEDDING_MODEL`             | settings.py        |
| `st_model_name`               | `ST_MODEL_NAME`               | settings.py        |
| `prediction_threshold`        | `PREDICTION_THRESHOLD`        | settings.py        |
| `confidence_decay_rate`       | `CONFIDENCE_DECAY_RATE`       | settings.py        |
| `confidence_growth_rate`      | `CONFIDENCE_GROWTH_RATE`      | settings.py        |
| `max_confidence`              | `MAX_CONFIDENCE`              | settings.py        |
| `min_confidence`              | `MIN_CONFIDENCE`              | settings.py        |
| `ambiguity_threshold`         | `AMBIGUITY_THRESHOLD`         | settings.py        |
| `top_k`                       | `TOP_K`                       | settings.py        |
| `dedup_similarity_threshold`  | `DEDUP_SIMILARITY_THRESHOLD`  | settings.py        |
| `backend_api_endpoint`        | `BACKEND_API_ENDPOINT`        | settings.py        |
| `backend_auth_token`          | `BACKEND_AUTH_TOKEN`          | settings.py        |

---

## S3 Bucket Structure

Matches `s3_service.py` exactly:

```
rag-bucket-pdf-filler/              (S3_BUCKET — primary)
  vectors/                          vector store
  log/{user_id}/{session_id}/{pdf_id}/
    overall_logs.jsonl              SessionLogger output
    api_logs.jsonl
    files_logs.jsonl

pdf-fillr-production/               (PROD_BUCKET — dual-write)
  {env}/{user_type}/{user_id}/sessions/{session_id}/rag/{pdf_id}/
  shared/filled_pdf_store/{env}/{user_id}/{session_id}/{pdf_id}/filled.pdf
  shared/unpredicted_fields/{env}/{user_id}/{session_id}/{pdf_id}/unpredicted_fields.json
```

---

## Logging

Three layers of logging are provisioned:

**1. CloudWatch** — Lambda stdout (all `logger.info/error` calls in lambda_function.py)
```bash
./scripts/logging.sh tail dev
./scripts/logging.sh errors dev 100
./scripts/logging.sh metrics dev
```

**2. S3 JSONL** — Session-scoped structured logs written by `SessionLogger`
```bash
./scripts/logging.sh s3logs dev <user_id> <session_id> <pdf_id>
```

**3. MS Teams** — Failure notifications via `teams_notifier.py` (webhook configured via `TEAMS_WEBHOOK_URL`)

---

## CloudWatch Alarms

Three alarms are provisioned and route to an SNS topic:

| Alarm             | Threshold                        |
|-------------------|----------------------------------|
| Lambda errors     | > 5 errors in 2 consecutive mins |
| Lambda duration   | p99 > 80% of timeout             |
| Lambda throttles  | > 10 throttles in 2 mins         |

Subscribe an email to the SNS topic to receive alerts:
```bash
aws sns subscribe \
  --topic-arn $(terraform output -raw aws_lambda_function_arn | sed 's/lambda/sns/') \
  --protocol email \
  --notification-endpoint your@email.com
```

---

## Constructor / Destructor

```bash
# Provision
./scripts/constructor.sh dev
./scripts/constructor.sh staging
./scripts/constructor.sh prod       # requires typing "yes" to confirm

# Tear down
./scripts/destructor.sh dev
./scripts/destructor.sh prod        # requires typing env name + "destroy"
```

---

## Multi-Cloud (Azure / GCP)

Azure and GCP modules are disabled by default. To enable:

```hcl
# in terraform.tfvars
enable_azure = true
azure_subscription_id     = "your-sub-id"
azure_resource_group_name = "rag-lambda-rg"
azure_location            = "East US"

enable_gcp   = true
gcp_project_id = "your-gcp-project"
gcp_region     = "asia-south1"
```

---

## Local Development

With `enable_local = true` (default in dev), Terraform generates:

- `.env.local` — all env vars pointing at LocalStack
- `docker-compose.local.yml` — LocalStack S3 + the Lambda container

```bash
# After terraform apply
docker compose -f docker-compose.local.yml up

# Invoke locally (Lambda RIE on port 9000)
curl -XPOST http://localhost:9000/2015-03-31/functions/function/invocations \
  -H "Content-Type: application/json" \
  -d '{"headers":{"x-api-key":"YOUR_KEY"},"body":"{\"api_name\":\"get_system_info\"}"}'
```

---

## Security Notes

- All secrets are stored in **AWS Secrets Manager** (not plaintext in Lambda env in prod — swap the `openai_api_key` etc. env vars for a secrets-manager fetch in `lambda_function.py` for hardened prod)
- Both S3 buckets have public access fully blocked
- S3 server-side encryption (AES-256) enabled on both buckets
- ECR image scanning on push enabled
- `force_destroy = false` on the production bucket — prevents accidental data loss
- prod Lambda has provisioned concurrency (2) to eliminate cold starts for heavy torch model
