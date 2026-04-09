variable "env" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "image_uri" {
  description = "ECR image URI (e.g. 123456789.dkr.ecr.us-east-1.amazonaws.com/mapper:latest)"
  type        = string
}

variable "llm_model" {
  description = "LLM model identifier (e.g. claude-3-5-sonnet-20241022, gpt-4o)"
  type        = string
  default     = "gpt-4o"
}

variable "rag_api_url" {
  description = "RAG service endpoint"
  type        = string
  default     = ""
}

# Lambda-specific
variable "lambda_memory_mb" {
  type    = number
  default = 2048
}

variable "lambda_timeout_sec" {
  type    = number
  default = 900
}

# ECS/Fargate-specific (used when deploy_mode = fargate)
variable "deploy_mode" {
  description = "lambda or fargate"
  type        = string
  default     = "lambda"
}

variable "vpc_id" {
  type    = string
  default = ""
}

variable "subnet_ids" {
  type    = list(string)
  default = []
}
