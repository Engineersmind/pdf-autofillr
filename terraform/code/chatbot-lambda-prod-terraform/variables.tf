##############################################################################
# variables.tf — prod chatbot lambda
# Every env var from the prod .env + codebase
##############################################################################

variable "environment" {
  type    = string
  default = "prod"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Must be dev, staging, or prod"
  }
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

# ── Lambda ────────────────────────────────────────────────────────────────────

variable "lambda_function_name" {
  type    = string
  default = "chatbot-prod"
}

variable "lambda_memory_mb" {
  description = <<-EOT
    1024 MB sufficient for langchain + fuzzywuzzy + openai + boto3.
    Prod requirements.txt does NOT include torch or sentence-transformers.
  EOT
  type    = number
  default = 1024
}

variable "lambda_timeout_seconds" {
  description = <<-EOT
    900s — same reasoning as dev:
      Step 5 polls 150s, Step 3 retry waits 180s, Step 6 retries 10×90s.
      _trigger_pdf_fill_async joins thread with timeout=250s.
  EOT
  type    = number
  default = 900
}


# ── S3 Buckets ────────────────────────────────────────────────────────────────
# NOTE: Same bucket names as dev. The prod separation happens via
# _ENV_FOLDER["prod_user"] = "prod" prefix inside pdf-fillr-production.

variable "output_bucket_name" {
  description = "OUTPUT_BUCKET — session state and chat outputs"
  type        = string
  default     = "chatbot-outputs-dev"
}

variable "static_bucket_name" {
  description = "STATIC_BUCKET — form_keys config + knowledge_store.json"
  type        = string
  default     = "chatbot-static-configs-usa-dev"
}

variable "prod_bucket_name" {
  description = "PROD_BUCKET — shared dual-write mirror"
  type        = string
  default     = "pdf-fillr-production"
}

# ── Downstream ────────────────────────────────────────────────────────────────

variable "fill_pdf_lambda_url" {
  description = <<-EOT
    FILL_PDF_LAMBDA_URL — PROD fill-pdf Lambda (different from dev).
    Dev:  5c242ihgrnjzrfw3ltathjb7jy0lxudt.lambda-url.us-east-1.on.aws
    Prod: 3udsn2n2xcnc7qdcfqncwi3sca0yrdff.lambda-url.us-east-1.on.aws
  EOT
  type    = string
  default = "https://3udsn2n2xcnc7qdcfqncwi3sca0yrdff.lambda-url.us-east-1.on.aws"
}

variable "backend_url" {
  description = <<-EOT
    BACKEND_URL — PROD backend API.
    Dev:  https://dev-autofiller-backend.engineersmind.dev
    Prod: https://api.pdffillr.ai/
  EOT
  type    = string
  default = "https://api.pdffillr.ai/"
}

variable "chatbot_env" {
  description = <<-EOT
    ENV — maps to PROD_BUCKET path prefix in s3_helper._ENV_FOLDER:
      prod_user → prod/
    Set to prod_user for production traffic.
  EOT
  type    = string
  default = "prod_user"
}

variable "notification_url" {
  description = "NOTIFICATION_URL — ChatbotNotifier (NOTIFICATIONS_ENABLED toggle)"
  type        = string
  default     = "https://dev-autofiller-backend.engineersmind.dev/events"
}

# ── Secrets ───────────────────────────────────────────────────────────────────

variable "auth_token" {
  description = "AUTH_TOKEN — Lambda X-API-Key gate"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OPENAI_API_KEY — gpt-4o-mini for all NLP in chatbot_core.py"
  type        = string
  sensitive   = true
}

variable "auth0_domain" {
  description = <<-EOT
    AUTH0_DOMAIN — PROD Auth0 tenant (different from dev).
    Prod: dev-ust08ro3ukgmtcrx.us.auth0.com
    Dev:  dev-gmmrk5nn7p2vndu8.us.auth0.com
  EOT
  type      = string
  sensitive = true
  default   = "dev-ust08ro3ukgmtcrx.us.auth0.com"
}

variable "auth0_client_id" {
  description = "AUTH0_CLIENT_ID — prod value: ZdwNOcyrlOMwt24cDHwtTEXb278E3QlM"
  type        = string
  sensitive   = true
  default     = ""
}

variable "auth0_client_secret" {
  description = "AUTH0_CLIENT_SECRET — prod secret (qKx92y...)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "auth0_audience" {
  description = "AUTH0_AUDIENCE — same in both envs"
  type        = string
  sensitive   = true
  default     = "https://aiformfiller-api.example.com"
}

variable "pdf_api_key" {
  description = "PDF_API_KEY — X-API-Key sent to fill-pdf Lambda"
  type        = string
  sensitive   = true
  default     = ""
}

variable "teams_webhook_url" {
  description = <<-EOT
    TEAMS_WEBHOOK_URL — ACTIVE in prod (no _remove suffix).
    In dev the .env key was TEAMS_WEBHOOK_URL_remove = disabled.
    In prod the .env key is TEAMS_WEBHOOK_URL = enabled.
    Set to the real Power Automate webhook URL.
  EOT
  type      = string
  sensitive = true
  default   = ""
}

variable "admin_username" {
  description = "ADMIN_USERNAME"
  type        = string
  sensitive   = true
  default     = ""
}

variable "admin_password" {
  description = "ADMIN_PASSWORD"
  type        = string
  sensitive   = true
  default     = ""
}

variable "x_event_key" {
  description = "X_EVENT_KEY — ChatbotNotifier event key"
  type        = string
  sensitive   = true
  default     = ""
}

# ── RDS ───────────────────────────────────────────────────────────────────────

variable "enable_rds" {
  description = "Create RDS PostgreSQL for rds_helper.py logging"
  type        = bool
  default     = false
}

variable "db_host"     { type = string; default = "" }
variable "db_port"     { type = string; default = "5432" }
variable "db_name"     { type = string; default = "chatbot" }
variable "db_user"     { type = string; sensitive = true; default = "" }
variable "db_password" { type = string; sensitive = true; default = "" }
variable "vpc_id"      { type = string; default = "" }
variable "rds_subnet_ids"    { type = list(string); default = [] }
variable "rds_ingress_cidrs" { type = list(string); default = [] }
