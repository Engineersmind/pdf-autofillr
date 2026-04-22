##############################################################################
# variables.tf — All input variables for rag-lambda Terraform
# Derived from: settings.py, .env, lambda_function.py, s3_service.py
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
  description = "AWS region for all resources"
  type        = string
  default     = "ap-south-1"
}

variable "rag_bucket_name" {
  description = "Primary RAG S3 bucket (S3_BUCKET in settings.py)"
  type        = string
  default     = "rag-bucket-pdf-filler"
}

variable "prod_bucket_name" {
  description = "Production dual-write S3 bucket (PROD_BUCKET in settings.py)"
  type        = string
  default     = "pdf-fillr-production"
}

variable "lambda_function_name" {
  description = "Lambda function name (RAG_LAMBDA_FUNCTION_NAME)"
  type        = string
  default     = "rag-pdf-filler"
}

variable "lambda_memory_mb" {
  description = "Lambda memory allocation in MB. Model (all-MiniLM-L6-v2) + torch needs ≥2048"
  type        = number
  default     = 3008
}

variable "lambda_timeout_seconds" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 300
}

variable "ecr_image_uri" {
  description = "Full ECR image URI (e.g. 123456789.dkr.ecr.ap-south-1.amazonaws.com/rag-lambda:latest)"
  type        = string
}

# ── Secrets (sensitive — set via TF_VAR_ env vars or AWS Secrets Manager) ───

variable "openai_api_key" {
  description = "OpenAI API key (OPENAI_API_KEY)"
  type        = string
  sensitive   = true
}

variable "x_api_key" {
  description = "Lambda gateway API key (X_API_KEY)"
  type        = string
  sensitive   = true
}

variable "teams_webhook_url" {
  description = "MS Teams Power Automate webhook URL (TEAMS_WEBHOOK_URL)"
  type        = string
  sensitive   = true
}

variable "backend_auth_token" {
  description = "Backend API auth token (BACKEND_AUTH_TOKEN)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "backend_api_endpoint" {
  description = "Backend API base URL (BACKEND_API_ENDPOINT)"
  type        = string
  default     = ""
}

# ── OpenAI / GPT-4 Settings (from settings.py) ──────────────────────────────

variable "gpt4_model" {
  description = "GPT-4 model name (GPT4_MODEL)"
  type        = string
  default     = "gpt-4-turbo-preview"
}

variable "gpt4_temperature" {
  description = "GPT-4 temperature (GPT4_TEMPERATURE)"
  type        = string
  default     = "0.3"
}

variable "gpt4_max_tokens" {
  description = "GPT-4 max tokens (GPT4_MAX_TOKENS)"
  type        = string
  default     = "500"
}

# ── Embedding / RAG Settings (from settings.py) ──────────────────────────────

variable "embedding_model" {
  description = "Embedding model type (EMBEDDING_MODEL)"
  type        = string
  default     = "sentence-transformer"
}

variable "st_model_name" {
  description = "SentenceTransformer model name (ST_MODEL_NAME)"
  type        = string
  default     = "all-MiniLM-L6-v2"
}

variable "prediction_threshold" {
  description = "Minimum confidence threshold for predictions (PREDICTION_THRESHOLD)"
  type        = string
  default     = "0.75"
}

variable "confidence_decay_rate" {
  description = "Confidence decay rate for bad vectors (CONFIDENCE_DECAY_RATE)"
  type        = string
  default     = "0.90"
}

variable "confidence_growth_rate" {
  description = "Confidence growth rate for good vectors (CONFIDENCE_GROWTH_RATE)"
  type        = string
  default     = "1.03"
}

variable "max_confidence" {
  description = "Maximum confidence cap (MAX_CONFIDENCE)"
  type        = string
  default     = "0.99"
}

variable "min_confidence" {
  description = "Minimum confidence floor (MIN_CONFIDENCE)"
  type        = string
  default     = "0.50"
}

variable "ambiguity_threshold" {
  description = "Ambiguity detection threshold (AMBIGUITY_THRESHOLD)"
  type        = string
  default     = "0.10"
}

variable "top_k" {
  description = "Top-K matches to retrieve (TOP_K)"
  type        = string
  default     = "5"
}

variable "dedup_similarity_threshold" {
  description = "Cosine similarity above which a vector is a duplicate (DEDUP_SIMILARITY_THRESHOLD)"
  type        = string
  default     = "0.92"
}

# ── Azure ────────────────────────────────────────────────────────────────────

variable "enable_azure" {
  description = "Deploy Azure mirror resources"
  type        = bool
  default     = false
}

variable "azure_subscription_id" {
  description = "Azure subscription ID"
  type        = string
  default     = ""
}

variable "azure_location" {
  description = "Azure region"
  type        = string
  default     = "East US"
}

variable "azure_resource_group_name" {
  description = "Azure resource group name"
  type        = string
  default     = "rag-lambda-rg"
}

# ── GCP ──────────────────────────────────────────────────────────────────────

variable "enable_gcp" {
  description = "Deploy GCP mirror resources"
  type        = bool
  default     = false
}

variable "gcp_project_id" {
  description = "GCP project ID"
  type        = string
  default     = ""
}

variable "gcp_region" {
  description = "GCP region"
  type        = string
  default     = "asia-south1"
}

# ── Local Docker ─────────────────────────────────────────────────────────────

variable "enable_local" {
  description = "Spin up local Docker Compose environment (dev only)"
  type        = bool
  default     = false
}
