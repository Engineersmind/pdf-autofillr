# ── Identity ──────────────────────────────────────────────────────────────────

variable "project" {
  description = "Project name prefix — used in all resource names"
  type        = string
  default     = "pdf-autofiller-mapper"
}

variable "env" {
  description = "Deployment environment: dev | prod"
  type        = string
  default     = "prod"

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
  description = "S3 URI for form_keys_flat.json — the target schema for Phase 1 mapping (e.g. s3://pdf-fillr-production/config/form_keys_flat.json)"
  type        = string
  default     = ""
}

# ── LLM ──────────────────────────────────────────────────────────────────────

variable "llm_model" {
  description = "LiteLLM model ID (e.g. gpt-4o, claude-3-5-sonnet-20241022)"
  type        = string
  default     = "gpt-4o"
}

variable "default_llm_provider" {
  description = "Default LLM provider: openai | claude"
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
  description = "LLM sampling temperature (0.0 = deterministic)"
  type        = number
  default     = 0.0
}

variable "llm_max_tokens" {
  description = "Max tokens for LLM completion responses"
  type        = number
  default     = 4096
}

variable "llm_timeout" {
  description = "LLM request timeout in seconds"
  type        = number
  default     = 120
}

variable "llm_max_retries" {
  description = "Max retries for LLM requests"
  type        = number
  default     = 3
}

variable "headers_llm_provider" {
  description = "LLM provider for headers extraction: openai | claude"
  type        = string
  default     = "openai"
}

variable "headers_openai_model_id" {
  description = "OpenAI model ID for headers extraction"
  type        = string
  default     = "gpt-4o"
}

variable "headers_claude_model_id" {
  description = "Claude model ID for headers extraction"
  type        = string
  default     = "claude-3-5-sonnet-20241022"
}

variable "headers_chunk_size" {
  description = "Number of form fields per LLM chunk for headers extraction"
  type        = number
  default     = 5
}

variable "headers_temperature" {
  description = "LLM temperature for headers extraction"
  type        = number
  default     = 0.0
}

variable "headers_max_tokens" {
  description = "Max tokens for headers extraction LLM calls"
  type        = number
  default     = 8192
}

# ── Auth ──────────────────────────────────────────────────────────────────────

variable "mapper_api_token" {
  description = "Bearer token callers must send in Authorization header to invoke the Lambda"
  type        = string
  sensitive   = true
}

variable "auth_api_base_url" {
  description = "Backend auth service base URL"
  type        = string
  default     = "https://dev-autofiller-backend.engineersmind.dev"
}

variable "auth_email" {
  description = "Email for backend auth (used by HTTP notifier)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "auth_password" {
  description = "Password for backend auth (used by HTTP notifier)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "auth_timeout_seconds" {
  description = "Auth client timeout in seconds"
  type        = number
  default     = 30
}

# ── RAG API ───────────────────────────────────────────────────────────────────
# Two separate Lambda URLs — one for dev, one for prod.
# The prod Lambda gets RAG_API_URL = prod URL; the dev Lambda gets the dev URL.

variable "rag_api_url" {
  description = "RAG Lambda Function URL for this environment (dev or prod)"
  type        = string
  default     = ""
}

variable "rag_api_key" {
  description = "X-API-Key header value for the RAG Lambda"
  type        = string
  sensitive   = true
  default     = ""
}

# ── Notifications ─────────────────────────────────────────────────────────────

variable "notifications_enabled" {
  description = "Enable pipeline status notifications to the backend"
  type        = bool
  default     = false
}

variable "notifications_backend_url" {
  description = "Backend webhook URL for pipeline status updates"
  type        = string
  default     = ""
}

variable "notifications_api_key" {
  description = "API key for the notifications backend"
  type        = string
  sensitive   = true
  default     = ""
}

# ── Lambda sizing ─────────────────────────────────────────────────────────────

variable "lambda_memory_mb" {
  description = "Lambda memory (MB). 3008 recommended — Java + LLM calls are memory-heavy."
  type        = number
  default     = 3008
}

variable "lambda_timeout_sec" {
  description = "Lambda timeout in seconds (max 900). make_embed is the slowest stage."
  type        = number
  default     = 900
}

variable "log_level" {
  description = "Application log level: DEBUG | INFO | WARNING | ERROR"
  type        = string
  default     = "INFO"
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}
