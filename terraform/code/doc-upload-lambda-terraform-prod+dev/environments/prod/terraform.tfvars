##############################################################################
# environments/prod/terraform.tfvars
##############################################################################

environment = "prod"
aws_region  = "us-east-1"

# Prod uses real bucket names without -dev suffix
static_bucket_name = "pdf-filler-function-usa"
output_bucket_name = "chatbot-outputs"
prod_bucket_name   = "pdf-fillr-production"

lambda_function_name   = "doc-upload"
lambda_memory_mb       = 1024
lambda_timeout_seconds = 600


fill_pdf_lambda_url = ""
backend_url         = "https://autofiller-backend.engineersmind.dev"

enable_local = false
enable_azure = false
enable_gcp   = false
