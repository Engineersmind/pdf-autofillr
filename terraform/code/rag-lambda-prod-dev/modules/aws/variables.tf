##############################################################################
# modules/aws/variables.tf
##############################################################################

variable "environment"           { type = string }
variable "aws_region"            { type = string }
variable "name_prefix"           { type = string }
variable "common_tags"           { type = map(string) }

variable "rag_bucket_name"       { type = string }
variable "prod_bucket_name"      { type = string }

variable "lambda_function_name"    { type = string }
variable "lambda_memory_mb"        { type = number }
variable "lambda_timeout_seconds"  { type = number }
variable "ecr_image_uri"           { type = string }

variable "openai_api_key"          { type = string; sensitive = true }
variable "x_api_key"               { type = string; sensitive = true }
variable "teams_webhook_url"        { type = string; sensitive = true }
variable "backend_auth_token"       { type = string; sensitive = true; default = "" }
variable "backend_api_endpoint"     { type = string; default = "" }

variable "gpt4_model"                   { type = string }
variable "gpt4_temperature"             { type = string }
variable "gpt4_max_tokens"              { type = string }
variable "embedding_model"              { type = string }
variable "st_model_name"                { type = string }
variable "prediction_threshold"         { type = string }
variable "confidence_decay_rate"        { type = string }
variable "confidence_growth_rate"       { type = string }
variable "max_confidence"               { type = string }
variable "min_confidence"               { type = string }
variable "ambiguity_threshold"          { type = string }
variable "top_k"                        { type = string }
variable "dedup_similarity_threshold"   { type = string }
