##############################################################################
# environments/staging/terraform.tfvars
##############################################################################

environment = "staging"
aws_region  = "ap-south-1"

rag_bucket_name  = "rag-bucket-pdf-filler-staging"
prod_bucket_name = "pdf-fillr-production-staging"

lambda_function_name   = "rag-pdf-filler-staging"
lambda_memory_mb       = 3008
lambda_timeout_seconds = 300

ecr_image_uri = "PLACEHOLDER"

gpt4_model       = "gpt-4-turbo-preview"
gpt4_temperature = "0.3"
gpt4_max_tokens  = "500"

embedding_model = "sentence-transformer"
st_model_name   = "all-MiniLM-L6-v2"

prediction_threshold       = "0.75"
confidence_decay_rate      = "0.90"
confidence_growth_rate     = "1.03"
max_confidence             = "0.99"
min_confidence             = "0.50"
ambiguity_threshold        = "0.10"
top_k                      = "5"
dedup_similarity_threshold = "0.92"

backend_api_endpoint = ""

enable_azure = false
enable_gcp   = false
enable_local = false
