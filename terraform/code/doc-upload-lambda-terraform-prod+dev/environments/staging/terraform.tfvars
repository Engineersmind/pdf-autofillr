##############################################################################
# environments/staging/terraform.tfvars
##############################################################################

environment = "staging"
aws_region  = "us-east-1"

static_bucket_name = "pdf-filler-function-usa-staging"
output_bucket_name = "chatbot-outputs-staging"
prod_bucket_name   = "pdf-fillr-production"

lambda_function_name   = "doc-upload-staging"
lambda_memory_mb       = 1024
lambda_timeout_seconds = 600


fill_pdf_lambda_url = ""
backend_url         = "https://staging-autofiller-backend.engineersmind.dev"

enable_local = false
enable_azure = false
enable_gcp   = false
