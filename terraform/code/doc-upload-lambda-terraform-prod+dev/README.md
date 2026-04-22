# doc-upload-lambda — Terraform Infrastructure

Infrastructure-as-code for the PDF extraction + filling pipeline Lambda.

---

## Architecture

```
                        ┌─────────────────────────────────────────────────┐
                        │  Lambda (this module)                           │
                        │                                                  │
  Client ──POST──▶      │  lambda_function.py                             │
  X-API-Key: AUTH_TOKEN │    │                                            │
                        │    └─▶ main.py ─ process_pdf()                  │
                        │           │                                      │
                        │    ┌──────┴──────┐                              │
                        │ Thread A       Thread B                          │
                        │  extractor     api_handler                       │
                        │  _logic.py     .py                               │
                        │    │ OpenAI        │ make_embed_file             │
                        │    │ gpt-4.1-mini  │ check_embed_file (polling) │
                        │    ▼               ▼                             │
                        │  S3 uploads   fill-pdf Lambda (HTTPS)           │
                        │  (3 buckets)                                     │
                        └─────────────────────────────────────────────────┘
```

**Thread A** (extractor_logic.py):
1. Download PDF from S3 via `s3_handler.download_pdf_to_tmp()`
2. Extract text (PyMuPDF / python-docx / python-pptx / openpyxl)
3. Call OpenAI `gpt-4.1-mini` for structured extraction
4. Upload nested JSON → `STATIC_BUCKET/outputs/...`
5. Upload flat JSON → `OUTPUT_BUCKET/{user_id}/sessions/{session_id}/final_output_flat.json`

**Thread B** (api_handler.py):
1. POST `make_embed_file` → fill-pdf Lambda
2. Poll `check_embed_file` (max 48 × 10s = 480s)

**After both threads**: POST `fill_pdf` → fill-pdf Lambda → done.

All S3 writes dual-write to `PROD_BUCKET` via `s3_handler.upload_json_to_s3()` and `logger_utils.APILogger`.

---

## Directory Structure

```
terraform/doc-upload-lambda/
├── main.tf                       # Wires all modules
├── variables.tf                  # All vars from .env + codebase
├── outputs.tf
├── .gitignore
│
├── modules/
│   ├── aws/                      # Lambda + 3 S3 buckets + ECR + IAM + CW + Secrets
│   ├── azure/                    # Blob Storage + Key Vault + ACR + App Insights
│   ├── gcp/                      # Cloud Storage + Secret Manager + Artifact Registry
│   └── local/                    # .env.local + docker-compose.local.yml
│
├── environments/
│   ├── dev/terraform.tfvars
│   ├── staging/terraform.tfvars
│   └── prod/terraform.tfvars
│
└── scripts/
    ├── bootstrap_backend.sh      # Create S3 state bucket + DynamoDB lock
    ├── constructor.sh            # Provision all infra
    ├── destructor.sh             # Tear down all infra
    ├── build_and_push.sh         # Build image → ECR → update Lambda
    └── logging.sh                # Tail logs, metrics, S3 log inspection
```

---

## Quick Start

### 1. Prerequisites
```bash
terraform >= 1.6
aws-cli >= 2.x
docker (with buildx linux/amd64)
jq
python3
```

### 2. Bootstrap state backend (once per account)
```bash
chmod +x scripts/*.sh
./scripts/bootstrap_backend.sh us-east-1
```

### 3. Export secrets
```bash
export TF_VAR_auth_token="7KmP@9xQ2NvL5!"
export TF_VAR_openai_api_key="sk-proj-..."
export TF_VAR_pdf_api_key="7KmP@9xQ2NvL5!"
export TF_VAR_teams_webhook_url="https://defaultb3869958..."
export TF_VAR_admin_username="subhamsuvendu98@gmail.com"
export TF_VAR_admin_password="..."
```

### 4. Provision
```bash
./scripts/constructor.sh dev
```

### 5. Build & push
```bash
./scripts/build_and_push.sh dev
```

---

## Environment Variables Mapped

| TF Variable          | Lambda Env Var        | Used In                                              |
|----------------------|-----------------------|------------------------------------------------------|
| `auth_token`         | `AUTH_TOKEN`          | lambda_function.py — header gate                     |
| `openai_api_key`     | `OPENAI_API_KEY`      | extractor_logic.py → gpt-4.1-mini                    |
| `pdf_api_key`        | `PDF_API_KEY`         | api_handler.py → fill-pdf Lambda X-API-Key           |
| `teams_webhook_url`  | `TEAMS_WEBHOOK_URL`   | teams_notifier.py — failure notifications            |
| `admin_password`     | `ADMIN_PASSWORD`      | backend admin auth                                   |
| `admin_username`     | `ADMIN_USERNAME`      | backend admin auth                                   |
| `static_bucket_name` | `STATIC_BUCKET`       | lambda_function.py, s3_handler.py, logger_utils.py   |
| `output_bucket_name` | `OUTPUT_BUCKET`       | main.py Thread A — flat JSON handoff                 |
| `prod_bucket_name`   | `PROD_BUCKET`         | s3_handler.py + logger_utils.py — dual-write         |
| `fill_pdf_lambda_url`| `FILL_PDF_LAMBDA_URL` | lambda_function.py → api_handler.py                  |
| `backend_url`        | `BACKEND_URL`         | backend API                                          |

---

## S3 Path Structure

```
STATIC_BUCKET (pdf-filler-function-usa-dev):
  config/
    form_keys.json                                  ← schema loaded at runtime
  outputs/
    {user_id}/sessions/{session_id}/{filled_doc_pdf_id}/
      final_upload_form_keys_filled.json            ← nested extraction result
      execution_logs.json                           ← APILogger flush + final save

OUTPUT_BUCKET (chatbot-outputs-dev):
  {user_id}/sessions/{session_id}/
    final_output_flat.json                          ← flat key-value handoff

PROD_BUCKET (pdf-fillr-production):  [dual-write from above]
  {env}/{user_type}/{user_id}/sessions/{session_id}/
    doc_upload/{filled_doc_pdf_id}/
      final_upload_form_keys_filled.json
      execution_logs.json
    final_output_flat.json
```

Where `env` = `local` | `dev` | `prod` (mapped from `Local_user` | `DEV_user` | `prod_user`)  
Where `user_type` = `sdk-user` (if developer_id present) | `regular`

---

## Logging

### CloudWatch
```bash
./scripts/logging.sh tail dev                         # live stream
./scripts/logging.sh errors dev 100                   # last 100 errors
./scripts/logging.sh metrics dev                      # invocations/errors/duration
./scripts/logging.sh teams dev                        # Teams failure notifications
```

### S3 Execution Logs
```bash
# Full pipeline trace for one session
./scripts/logging.sh pipeline dev <user_id> <session_id> <filled_doc_pdf_id>

# Raw execution_logs.json with parsed summary
./scripts/logging.sh s3logs dev <user_id> <session_id> <filled_doc_pdf_id>
```

### CloudWatch Alarms (auto-provisioned)
| Alarm | Threshold |
|-------|-----------|
| Lambda errors | > 3 in 2 min |
| Lambda p95 duration | > 80% of timeout |
| Lambda throttles | > 5 in 2 min |
| Teams pipeline failures | > 0 in 5 min |

---

## Constructor / Destructor

```bash
./scripts/constructor.sh dev
./scripts/constructor.sh staging
./scripts/constructor.sh prod     # requires typing 'yes'

./scripts/destructor.sh dev
./scripts/destructor.sh prod      # requires env name + 'destroy'
```

---

## Lambda Timeout Reasoning

| Thread | Max duration |
|--------|-------------|
| Thread B (polling) | 48 × 10s = **480s** |
| Thread A (OpenAI) | ~30–60s typical |
| fill_pdf API call | timeout=200s |
| Total (parallel A‖B then fill_pdf) | ~680s worst case |

**Lambda timeout is set to 600s** (10 min). If your embed polling consistently hits 480s, reduce `max_attempts` in `api_handler.check_embed_file()` or increase the Lambda timeout.

---

## Important: prod_bucket is Shared

`pdf-fillr-production` is written to by **both** `rag-lambda` and `doc-upload-lambda`. If you run both Terraform modules, import the bucket into only one and reference it in the other to avoid state conflicts:

```bash
# If rag-lambda already created it:
terraform import module.aws.aws_s3_bucket.prod pdf-fillr-production
```
