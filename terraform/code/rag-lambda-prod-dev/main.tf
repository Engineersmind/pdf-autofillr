##############################################################################
# rag-lambda — Root Terraform Configuration
# Deploys the RAG PDF-Filler Lambda across AWS / Azure / GCP / Local
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
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  # Remote state — swap to azurerm/gcs backend as needed
  backend "s3" {
    bucket         = "rag-lambda-tfstate"
    key            = "rag-lambda/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "rag-lambda-tflock"
    encrypt        = true
  }
}

# ── Provider Configuration ───────────────────────────────────────────────────

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

# ── Local Values ─────────────────────────────────────────────────────────────

locals {
  name_prefix = "rag-lambda-${var.environment}"

  common_tags = {
    Project     = "pdf-fillr"
    Service     = "rag-lambda"
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  # Env → S3 folder mapping  (matches _ENV_FOLDER in s3_service.py)
  env_folder = {
    dev     = "dev"
    staging = "dev"   # staging still writes to dev folder in prod bucket
    prod    = "prod"
  }
}

# ── Module: AWS (primary runtime) ───────────────────────────────────────────

module "aws" {
  source = "./modules/aws"

  environment      = var.environment
  aws_region       = var.aws_region
  name_prefix      = local.name_prefix
  common_tags      = local.common_tags

  # S3 Buckets (derived from s3_service.py + settings.py)
  rag_bucket_name  = var.rag_bucket_name        # S3_BUCKET = rag-bucket-pdf-filler
  prod_bucket_name = var.prod_bucket_name       # PROD_BUCKET = pdf-fillr-production

  # Lambda config
  lambda_function_name    = var.lambda_function_name  # RAG_LAMBDA_FUNCTION_NAME
  lambda_memory_mb        = var.lambda_memory_mb
  lambda_timeout_seconds  = var.lambda_timeout_seconds
  ecr_image_uri           = var.ecr_image_uri

  # Secrets (never stored in tfvars — fetched from Secrets Manager)
  openai_api_key     = var.openai_api_key
  x_api_key          = var.x_api_key
  teams_webhook_url  = var.teams_webhook_url
  backend_auth_token = var.backend_auth_token

  # App settings (from settings.py)
  gpt4_model              = var.gpt4_model
  gpt4_temperature        = var.gpt4_temperature
  gpt4_max_tokens         = var.gpt4_max_tokens
  st_model_name           = var.st_model_name
  embedding_model         = var.embedding_model
  prediction_threshold    = var.prediction_threshold
  confidence_decay_rate   = var.confidence_decay_rate
  confidence_growth_rate  = var.confidence_growth_rate
  max_confidence          = var.max_confidence
  min_confidence          = var.min_confidence
  ambiguity_threshold     = var.ambiguity_threshold
  top_k                   = var.top_k
  dedup_similarity_threshold = var.dedup_similarity_threshold

  backend_api_endpoint    = var.backend_api_endpoint
}

# ── Module: Azure (optional mirror) ─────────────────────────────────────────

module "azure" {
  source = "./modules/azure"
  count  = var.enable_azure ? 1 : 0

  environment         = var.environment
  azure_location      = var.azure_location
  name_prefix         = local.name_prefix
  common_tags         = local.common_tags
  resource_group_name = var.azure_resource_group_name

  openai_api_key    = var.openai_api_key
  x_api_key         = var.x_api_key
  teams_webhook_url = var.teams_webhook_url
}

# ── Module: GCP (optional mirror) ───────────────────────────────────────────

module "gcp" {
  source = "./modules/gcp"
  count  = var.enable_gcp ? 1 : 0

  environment    = var.environment
  gcp_project_id = var.gcp_project_id
  gcp_region     = var.gcp_region
  name_prefix    = local.name_prefix

  openai_api_key    = var.openai_api_key
  x_api_key         = var.x_api_key
  teams_webhook_url = var.teams_webhook_url
}

# ── Module: Local Docker (dev only) ─────────────────────────────────────────

module "local" {
  source = "./modules/local"
  count  = var.enable_local ? 1 : 0

  environment      = var.environment
  name_prefix      = local.name_prefix

  rag_bucket_name  = var.rag_bucket_name
  prod_bucket_name = var.prod_bucket_name

  openai_api_key          = var.openai_api_key
  x_api_key               = var.x_api_key
  teams_webhook_url       = var.teams_webhook_url
  backend_auth_token      = var.backend_auth_token
  backend_api_endpoint    = var.backend_api_endpoint
  gpt4_model              = var.gpt4_model
  st_model_name           = var.st_model_name
  prediction_threshold    = var.prediction_threshold
  top_k                   = var.top_k
}
