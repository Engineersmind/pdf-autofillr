##############################################################################
# environments/dev/terraform.tfvars
# Development — safe to commit. No secrets here.
#
# Secrets — export as TF_VAR_ before running constructor.sh:
#   export TF_VAR_auth_token="7KmP@9xQ2NvL5!"
#   export TF_VAR_openai_api_key="sk-proj-..."
#   export TF_VAR_pdf_api_key="7KmP@9xQ2NvL5!"
#   export TF_VAR_teams_webhook_url="https://..."
#   export TF_VAR_admin_username="subhamsuvendu98@gmail.com"
#   export TF_VAR_admin_password="..."
##############################################################################

environment = "dev"
aws_region  = "us-east-1"

# S3 Buckets — from .env
static_bucket_name = "pdf-filler-function-usa-dev"
output_bucket_name = "chatbot-outputs-dev"
prod_bucket_name   = "pdf-fillr-production"

# Lambda
lambda_function_name   = "doc-upload-dev"
lambda_memory_mb       = 1024
lambda_timeout_seconds = 600   # Thread B max: 48×10s=480s + Thread A OpenAI + fill_pdf(200s)


# Downstream fill-pdf Lambda (from .env)
fill_pdf_lambda_url = "https://5c242ihgrnjzrfw3ltathjb7jy0lxudt.lambda-url.us-east-1.on.aws"
backend_url         = "https://dev-autofiller-backend.engineersmind.dev"

# Local docker dev environment
enable_local = true

# Multi-cloud disabled in dev
enable_azure = false
enable_gcp   = false
