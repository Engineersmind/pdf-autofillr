##############################################################################
# doc-upload-lambda — Root Terraform Configuration
#
# Codebase analysis:
#   lambda_function.py  — Lambda handler, reads AUTH_TOKEN, routes to process_pdf()
#   main.py             — Parallel pipeline: Thread A (extract+upload) + Thread B (embed+poll)
#   extractor_logic.py  — PyMuPDF/DOCX/PPTX/XLSX extraction → OpenAI gpt-4.1-mini
#   api_handler.py      — Calls fill-pdf Lambda: make_embed_file → check_embed_file → fill_pdf
#   s3_handler.py       — S3 download/upload with dual-write to PROD_BUCKET
#   logger_utils.py     — APILogger: in-memory + S3 JSONL flush + prod bucket dup
#   teams_notifier.py   — Silent MS Teams webhook on failure
#
# S3 buckets (from .env + s3_handler.py):
#   STATIC_BUCKET  = pdf-filler-function-usa-dev   (schema + outputs)
#   OUTPUT_BUCKET  = chatbot-outputs-dev            (flat JSON handoff)
#   PROD_BUCKET    = pdf-fillr-production           (dual-write mirror)
#
# Downstream Lambda (called via HTTP, NOT invoked directly):
#   FILL_PDF_LAMBDA_URL — external Lambda URL, no IAM needed here
##############################################################################

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.0"
    }
  }

  backend "s3" {
    bucket         = "doc-upload-tfstate"
    key            = "doc-upload-lambda/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "doc-upload-tflock"
    encrypt        = true
  }
}

# ── Providers ─────────────────────────────────────────────────────────────────

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = local.common_tags
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.azure_subscription_id
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# ── Locals ────────────────────────────────────────────────────────────────────

locals {
  name_prefix = "doc-upload-${var.environment}"

  common_tags = {
    Project     = "pdf-fillr"
    Service     = "doc-upload-lambda"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# ── AWS (primary) ─────────────────────────────────────────────────────────────

module "aws" {
  source = "./modules/aws"

  environment  = var.environment
  aws_region   = var.aws_region
  name_prefix  = local.name_prefix
  common_tags  = local.common_tags

  # Lambda packaging
  lambda_function_name   = var.lambda_function_name
  lambda_memory_mb       = var.lambda_memory_mb
  lambda_timeout_seconds = var.lambda_timeout_seconds

  # S3 Buckets — derived from s3_handler.py + .env
  static_bucket_name = var.static_bucket_name   # STATIC_BUCKET: schema + per-session outputs
  output_bucket_name = var.output_bucket_name   # OUTPUT_BUCKET: flat JSON handoff
  prod_bucket_name   = var.prod_bucket_name     # PROD_BUCKET:   dual-write mirror

  # Secrets (sensitive — set via TF_VAR_ env vars)
  auth_token        = var.auth_token           # AUTH_TOKEN (X-API-Key gate on this Lambda)
  openai_api_key    = var.openai_api_key       # OPENAI_API_KEY
  pdf_api_key       = var.pdf_api_key          # PDF_API_KEY (passed to fill-pdf Lambda)
  teams_webhook_url = var.teams_webhook_url    # TEAMS_WEBHOOK_URL
  admin_password    = var.admin_password       # ADMIN_PASSWORD
  admin_username    = var.admin_username       # ADMIN_USERNAME

  # Non-secret config
  fill_pdf_lambda_url = var.fill_pdf_lambda_url  # FILL_PDF_LAMBDA_URL
  backend_url         = var.backend_url           # BACKEND_URL
}

# ── Azure (optional) ──────────────────────────────────────────────────────────

module "azure" {
  source = "./modules/azure"
  count  = var.enable_azure ? 1 : 0

  environment         = var.environment
  azure_location      = var.azure_location
  name_prefix         = local.name_prefix
  common_tags         = local.common_tags
  resource_group_name = var.azure_resource_group_name

  auth_token        = var.auth_token
  openai_api_key    = var.openai_api_key
  pdf_api_key       = var.pdf_api_key
  teams_webhook_url = var.teams_webhook_url
}

# ── GCP (optional) ────────────────────────────────────────────────────────────

module "gcp" {
  source = "./modules/gcp"
  count  = var.enable_gcp ? 1 : 0

  environment    = var.environment
  gcp_project_id = var.gcp_project_id
  gcp_region     = var.gcp_region
  name_prefix    = local.name_prefix

  auth_token        = var.auth_token
  openai_api_key    = var.openai_api_key
  pdf_api_key       = var.pdf_api_key
  teams_webhook_url = var.teams_webhook_url
}

# ── Local Docker (dev only) ───────────────────────────────────────────────────

module "local" {
  source = "./modules/local"
  count  = var.enable_local ? 1 : 0

  environment         = var.environment
  name_prefix         = local.name_prefix
  static_bucket_name  = var.static_bucket_name
  output_bucket_name  = var.output_bucket_name
  prod_bucket_name    = var.prod_bucket_name
  auth_token          = var.auth_token
  openai_api_key      = var.openai_api_key
  pdf_api_key         = var.pdf_api_key
  teams_webhook_url   = var.teams_webhook_url
  fill_pdf_lambda_url = var.fill_pdf_lambda_url
  backend_url         = var.backend_url
}
