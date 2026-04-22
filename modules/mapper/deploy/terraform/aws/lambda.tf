# ---------------------------------------------------------------------------
# CloudWatch log group — created before the function so retention is set
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "mapper" {
  name              = "/aws/lambda/${local.name}"
  retention_in_days = var.log_retention_days
}

# ---------------------------------------------------------------------------
# Lambda — PDF autofiller mapper
#
# Same Docker image as local/FastAPI. DEPLOY_MODE=lambda switches
# the entrypoint to entrypoints/aws_lambda.py::lambda_handler.
# ---------------------------------------------------------------------------

resource "aws_lambda_function" "mapper" {
  function_name = local.name
  description   = "PDF field extraction, semantic mapping, embedding and filling"
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.mapper.repository_url}:latest"
  timeout       = var.lambda_timeout_sec
  memory_size   = var.lambda_memory_mb

  ephemeral_storage {
    size = 2048  # /tmp for intermediate PDF/JSON files during processing
  }

  environment {
    variables = {
      # Runtime
      DEPLOY_MODE            = "lambda"
      LOG_LEVEL              = var.log_level

      # Storage — buckets already exist, we just point at them
      MAPPER_STORAGE         = "aws"
      CLOUD_PROVIDER         = "aws"
      AWS_S3_BUCKET          = var.s3_bucket
      MAPPER_S3_BUCKET       = var.s3_bucket
      MAPPER_ENV             = local.mapper_env
      MAPPER_PROCESSING_PATH = "/tmp/processing"

      # LLM
      LLM_MODEL            = var.llm_model
      LLM_TEMPERATURE      = tostring(var.llm_temperature)
      LLM_MAX_TOKENS       = tostring(var.llm_max_tokens)
      LLM_TIMEOUT          = tostring(var.llm_timeout)
      LLM_MAX_RETRIES      = tostring(var.llm_max_retries)
      DEFAULT_LLM_PROVIDER = var.default_llm_provider
      OPENAI_API_KEY       = var.openai_api_key
      ANTHROPIC_API_KEY    = var.anthropic_api_key

      # Headers extraction LLM
      HEADERS_LLM_PROVIDER      = var.headers_llm_provider
      HEADERS_OPENAI_MODEL_ID   = var.headers_openai_model_id
      HEADERS_CLAUDE_MODEL_ID   = var.headers_claude_model_id
      HEADERS_CHUNK_SIZE        = tostring(var.headers_chunk_size)
      HEADERS_TEMPERATURE       = tostring(var.headers_temperature)
      HEADERS_MAX_TOKENS        = tostring(var.headers_max_tokens)

      # Auth
      MAPPER_LAMBDA_API_TOKEN = var.mapper_api_token
      AUTH_API_BASE_URL       = var.auth_api_base_url
      AUTH_EMAIL              = var.auth_email
      AUTH_PASSWORD           = var.auth_password
      AUTH_TIMEOUT_SECONDS    = tostring(var.auth_timeout_seconds)

      # RAG API — each env (dev/prod) has its own Lambda URL in tfvars.
      # RAG_MODE flips to http automatically when a URL is provided.
      RAG_MODE    = var.rag_api_url != "" ? "http" : "inprocess"
      RAG_API_URL = var.rag_api_url
      RAG_API_KEY = var.rag_api_key

      # PDF hash cache
      PDF_CACHE_ENABLED = "true"
      PDF_CACHE_BUCKET  = local.cache_bucket

      # Global form keys schema
      GLOBAL_INPUT_JSON_S3_URI = var.global_input_json_s3_uri

      # Notifications (off by default)
      NOTIFICATIONS_ENABLED     = tostring(var.notifications_enabled)
      NOTIFICATIONS_BACKEND_URL = var.notifications_backend_url
      NOTIFICATIONS_API_KEY     = var.notifications_api_key
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.mapper,
    aws_iam_role_policy_attachment.lambda_basic,
    aws_iam_role_policy.lambda_permissions,
  ]
}

# Disable automatic retries — a failed invocation should not reprocess
resource "aws_lambda_function_event_invoke_config" "mapper" {
  function_name          = aws_lambda_function.mapper.function_name
  maximum_retry_attempts = 0
}

# ---------------------------------------------------------------------------
# Lambda Function URL — public HTTPS endpoint, auth handled by
# MAPPER_LAMBDA_API_TOKEN at the application layer
# ---------------------------------------------------------------------------

resource "aws_lambda_function_url" "mapper" {
  function_name      = aws_lambda_function.mapper.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["*"]
    allow_methods = ["POST"]
    allow_headers = ["Content-Type", "Authorization"]
    max_age       = 300
  }
}
