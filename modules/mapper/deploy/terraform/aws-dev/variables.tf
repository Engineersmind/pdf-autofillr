# ── Identity ──────────────────────────────────────────────────────────────────

variable "project" {
  description = "Project name prefix — used in all resource names"
  type        = string
  default     = "pdf-autofiller-mapper"
}

variable "env" {
  description = "Deployment environment: dev | prod"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "prod"], var.env)
    error_message = "env must be 'dev' or 'prod'."
  }
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

# ── ECR override ──────────────────────────────────────────────────────────────
# The dev ECR repo was created manually with a non-standard name.
# Set this to match the existing repo name so Terraform can import it.

variable "ecr_repository_name" {
  description = "ECR repository name. Overrides the default {project}-{env} naming when set."
  type        = string
  default     = ""
}

# ── Storage ───────────────────────────────────────────────────────────────────

variable "s3_bucket" {
  description = "Primary S3 bucket for all pipeline data (inputs, outputs, cache)"
  type        = string
  default     = "pdf-fillr-production"
}

variable "pdf_cache_bucket" {
  description = "S3 bucket for PDF hash cache. Defaults to s3_bucket if empty."
  type        = string
  default     = ""
}

variable "global_input_json_s3_uri" {
  description = "S3 URI for form_keys_flat.json — the target schema for Phase 1 mapping"
  type        = string
  default     = ""
}

# ── LLM ──────────────────────────────────────────────────────────────────────

variable "llm_model" {
  description = "LiteLLM model ID (e.g. gpt-4o, bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0)"
  type        = string
  default     = "gpt-4o"
}

variable "default_llm_provider" {
  description = "Default LLM provider: openai | bedrock | claude"
  type        = string
  default     = "openai"
}

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "anthropic_api_key" {
  description = "Anthropic API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "llm_temperature" {
  type    = number
  default = 0.0
}

variable "llm_max_tokens" {
  type    = number
  default = 4096
}

variable "llm_timeout" {
  type    = number
  default = 120
}

variable "llm_max_retries" {
  type    = number
  default = 3
}

variable "headers_llm_provider" {
  type    = string
  default = "openai"
}

variable "headers_openai_model_id" {
  type    = string
  default = "gpt-4o"
}

variable "headers_claude_model_id" {
  type    = string
  default = "claude-3-5-sonnet-20241022"
}

variable "headers_chunk_size" {
  type    = number
  default = 5
}

variable "headers_temperature" {
  type    = number
  default = 0.0
}

variable "headers_max_tokens" {
  type    = number
  default = 8192
}

# ── Auth ──────────────────────────────────────────────────────────────────────

variable "mapper_api_token" {
  description = "X-API-Key token callers must send to invoke the Lambda"
  type        = string
  sensitive   = true
}

variable "auth_api_base_url" {
  description = "Backend auth service base URL"
  type        = string
  default     = "https://dev-autofiller-backend.engineersmind.dev"
}

variable "auth_email" {
  type      = string
  sensitive = true
  default   = ""
}

variable "auth_password" {
  type      = string
  sensitive = true
  default   = ""
}

variable "auth_timeout_seconds" {
  type    = number
  default = 30
}

# ── RAG API ───────────────────────────────────────────────────────────────────

variable "rag_api_url" {
  description = "Dev RAG Lambda Function URL"
  type        = string
  default     = ""
}

variable "rag_api_key" {
  description = "X-API-Key for the dev RAG Lambda"
  type        = string
  sensitive   = true
  default     = ""
}

# ── Notifications ─────────────────────────────────────────────────────────────

variable "notifications_enabled" {
  type    = bool
  default = false
}

variable "notifications_backend_url" {
  type    = string
  default = ""
}

variable "notifications_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

# ── Lambda sizing — dev defaults are lighter than prod ────────────────────────

variable "lambda_memory_mb" {
  description = "Lambda memory in MB"
  type        = number
  default     = 2048
}

variable "lambda_timeout_sec" {
  description = "Lambda timeout in seconds (max 900)"
  type        = number
  default     = 900
}

variable "log_level" {
  description = "Application log level: DEBUG | INFO | WARNING | ERROR"
  type        = string
  default     = "DEBUG"
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

# ── S3 buckets for IAM ────────────────────────────────────────────────────────

variable "rag_bucket" {
  description = "RAG S3 bucket name"
  type        = string
  default     = "rag-bucket-pdf-filler"
}

variable "uploads_bucket" {
  description = "S3 bucket where backend uploads raw PDFs (mapper needs read access)"
  type        = string
  default     = "pdf-autofiller-dev"
}
