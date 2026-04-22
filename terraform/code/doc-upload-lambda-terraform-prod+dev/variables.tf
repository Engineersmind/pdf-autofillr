##############################################################################
# variables.tf
# Every variable derived from:
#   .env, lambda_function.py, main.py, s3_handler.py, logger_utils.py
##############################################################################

# ── Environment ──────────────────────────────────────────────────────────────

variable "environment" {
  description = "Deployment environment: dev | staging | prod"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging, or prod"
  }
}

# ── AWS ──────────────────────────────────────────────────────────────────────

variable "aws_region" {
  description = "AWS region. Lambda URL in .env is us-east-1."
  type        = string
  default     = "us-east-1"
}

# ── Lambda ────────────────────────────────────────────────────────────────────

variable "lambda_function_name" {
  description = "Name of this extractor Lambda function"
  type        = string
  default     = "doc-upload"
}

variable "lambda_memory_mb" {
  description = <<-EOT
    Memory in MB.
    PyMuPDF + Pillow + python-docx + openpyxl + python-pptx are moderate.
    1024 MB is sufficient; raise if large XLSX/PPTX cause OOM.
  EOT
  type    = number
  default = 1024
}

variable "lambda_timeout_seconds" {
  description = <<-EOT
    Timeout in seconds.
    main.py polls embed file up to 48 × 10s = 480s in Thread B.
    api_handler.py fill_pdf timeout = 200s.
    Set to 600 to safely cover both threads running in parallel.
  EOT
  type    = number
  default = 600
}


# ── S3 Buckets ────────────────────────────────────────────────────────────────
# Derived from s3_handler.py env vars + .env

variable "static_bucket_name" {
  description = <<-EOT
    STATIC_BUCKET — stores:
      config/form_keys.json  (schema)
      outputs/{user_id}/sessions/{session_id}/{filled_doc_pdf_id}/
        final_upload_form_keys_filled.json
        execution_logs.json
  EOT
  type    = string
  default = "pdf-filler-function-usa-dev"
}

variable "output_bucket_name" {
  description = <<-EOT
    OUTPUT_BUCKET — stores flat JSON handoff:
      {user_id}/sessions/{session_id}/final_output_flat.json
  EOT
  type    = string
  default = "chatbot-outputs-dev"
}

variable "prod_bucket_name" {
  description = <<-EOT
    PROD_BUCKET — dual-write mirror (s3_handler.py + logger_utils.py).
    Path patterns written here:
      {env}/{user_type}/{user_id}/sessions/{session_id}/doc_upload/{filled_doc_pdf_id}/{filename}
      {env}/{user_type}/{user_id}/sessions/{session_id}/final_output_flat.json
      {env}/{user_type}/{user_id}/sessions/{session_id}/doc_upload/{filled_doc_pdf_id}/execution_logs.json
  EOT
  type    = string
  default = "pdf-fillr-production"
}

# ── Secrets (sensitive — always use TF_VAR_ env vars, never hardcode) ────────

variable "auth_token" {
  description = <<-EOT
    AUTH_TOKEN — guards this Lambda's own endpoint.
    lambda_function.py checks headers["x-api-key"] == AUTH_TOKEN.
    Same value as X_API_KEY on the other Lambda.
  EOT
  type      = string
  sensitive = true
}

variable "openai_api_key" {
  description = "OPENAI_API_KEY — used by extractor_logic.py → call_llm() → gpt-4.1-mini"
  type        = string
  sensitive   = true
}

variable "pdf_api_key" {
  description = <<-EOT
    PDF_API_KEY — passed as X-API-Key header to fill-pdf Lambda
    by api_handler.py._make_request().
  EOT
  type      = string
  sensitive = true
}

variable "teams_webhook_url" {
  description = "TEAMS_WEBHOOK_URL — Power Automate webhook for failure notifications"
  type        = string
  sensitive   = true
}

variable "admin_password" {
  description = "ADMIN_PASSWORD — backend admin credential"
  type        = string
  sensitive   = true
  default     = ""
}

variable "admin_username" {
  description = "ADMIN_USERNAME — backend admin credential"
  type        = string
  sensitive   = true
  default     = ""
}

# ── Non-secret Config ─────────────────────────────────────────────────────────

variable "fill_pdf_lambda_url" {
  description = <<-EOT
    FILL_PDF_LAMBDA_URL — HTTP URL of the downstream fill-pdf Lambda.
    Called by api_handler.py (not invoked via IAM — plain HTTPS POST).
    Example: https://5c242ihgrnjzrfw3ltathjb7jy0lxudt.lambda-url.us-east-1.on.aws
  EOT
  type    = string
  default = ""
}

variable "backend_url" {
  description = "BACKEND_URL — backend API base URL"
  type        = string
  default     = ""
}

# ── Multi-cloud toggles ───────────────────────────────────────────────────────

variable "enable_azure" {
  type    = bool
  default = false
}

variable "azure_subscription_id" {
  type    = string
  default = ""
}

variable "azure_location" {
  type    = string
  default = "East US"
}

variable "azure_resource_group_name" {
  type    = string
  default = "doc-upload-rg"
}

variable "enable_gcp" {
  type    = bool
  default = false
}

variable "gcp_project_id" {
  type    = string
  default = ""
}

variable "gcp_region" {
  type    = string
  default = "us-east1"
}

variable "enable_local" {
  description = "Generate .env.local + docker-compose.local.yml for local dev"
  type        = bool
  default     = false
}
