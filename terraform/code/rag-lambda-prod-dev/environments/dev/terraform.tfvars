##############################################################################
# environments/dev/terraform.tfvars
# Development environment — safe to commit (no secrets here)
##############################################################################

environment = "dev"
aws_region  = "ap-south-1"

# S3 Buckets
rag_bucket_name  = "rag-bucket-pdf-filler-dev"
prod_bucket_name = "pdf-fillr-production-dev"

# Lambda
lambda_function_name   = "rag-pdf-filler-dev"
lambda_memory_mb       = 3008
lambda_timeout_seconds = 300

# ECR image — set this to your actual image after first docker build + push
ecr_image_uri = "PLACEHOLDER — run: ./scripts/build_and_push.sh dev"

# OpenAI
gpt4_model       = "gpt-4-turbo-preview"
gpt4_temperature = "0.3"
gpt4_max_tokens  = "500"

# Embedding
embedding_model = "sentence-transformer"
st_model_name   = "all-MiniLM-L6-v2"

# RAG / Confidence
prediction_threshold       = "0.75"
confidence_decay_rate      = "0.90"
confidence_growth_rate     = "1.03"
max_confidence             = "0.99"
min_confidence             = "0.50"
ambiguity_threshold        = "0.10"
top_k                      = "5"
dedup_similarity_threshold = "0.92"

# Backend
backend_api_endpoint = ""

# Cloud toggles
enable_azure = false
enable_gcp   = false
enable_local = true

# Secrets — set via TF_VAR_ environment variables, NOT here:
#   export TF_VAR_openai_api_key="sk-..."
#   export TF_VAR_x_api_key="7KmP@9xQ2NvL5!"
#   export TF_VAR_teams_webhook_url="https://..."
#   export TF_VAR_backend_auth_token="..."
