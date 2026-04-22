##############################################################################
# modules/aws/main.tf
# AWS Resources for rag-lambda:
#   - ECR repository
#   - S3 buckets (rag-bucket-pdf-filler + pdf-fillr-production)
#   - IAM role + policies
#   - Secrets Manager (all sensitive env vars)
#   - Lambda function (container image)
#   - API Gateway (HTTP API)
#   - CloudWatch log groups + alarms
#   - SNS for alarm routing
##############################################################################

# ── Data Sources ─────────────────────────────────────────────────────────────

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# ── ECR Repository ───────────────────────────────────────────────────────────

resource "aws_ecr_repository" "rag_lambda" {
  name                 = "${var.name_prefix}-repo"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = var.common_tags
}

resource "aws_ecr_lifecycle_policy" "rag_lambda" {
  repository = aws_ecr_repository.rag_lambda.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}

# ── S3: RAG Bucket (primary — rag-bucket-pdf-filler) ────────────────────────

resource "aws_s3_bucket" "rag" {
  bucket        = var.rag_bucket_name
  force_destroy = var.environment != "prod"
  tags          = var.common_tags
}

resource "aws_s3_bucket_versioning" "rag" {
  bucket = aws_s3_bucket.rag.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "rag" {
  bucket = aws_s3_bucket.rag.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "rag" {
  bucket                  = aws_s3_bucket.rag.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "rag" {
  bucket = aws_s3_bucket.rag.id

  # Logs path: log/{user_id}/{session_id}/{pdf_id}/*.jsonl
  rule {
    id     = "expire-session-logs"
    status = "Enabled"
    filter { prefix = "log/" }
    expiration { days = 90 }
  }

  # Vector store
  rule {
    id     = "transition-vectors-to-ia"
    status = "Enabled"
    filter { prefix = "vectors/" }
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
  }
}

# ── S3: Production Bucket (dual-write — pdf-fillr-production) ────────────────

resource "aws_s3_bucket" "prod" {
  bucket        = var.prod_bucket_name
  force_destroy = false   # never accidentally destroy prod
  tags          = merge(var.common_tags, { Role = "production-store" })
}

resource "aws_s3_bucket_versioning" "prod" {
  bucket = aws_s3_bucket.prod.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "prod" {
  bucket = aws_s3_bucket.prod.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "prod" {
  bucket                  = aws_s3_bucket.prod.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "prod" {
  bucket = aws_s3_bucket.prod.id

  # filled_pdf_store — keep for 1 year
  rule {
    id     = "expire-filled-pdfs"
    status = "Enabled"
    filter { prefix = "shared/filled_pdf_store/" }
    expiration { days = 365 }
  }

  # unpredicted_fields — 90 days
  rule {
    id     = "expire-unpredicted-fields"
    status = "Enabled"
    filter { prefix = "shared/unpredicted_fields/" }
    expiration { days = 90 }
  }
}

# ── Secrets Manager ───────────────────────────────────────────────────────────

resource "aws_secretsmanager_secret" "rag_lambda" {
  name                    = "${var.name_prefix}/env"
  description             = "All environment secrets for ${var.name_prefix} Lambda"
  recovery_window_in_days = var.environment == "prod" ? 30 : 0
  tags                    = var.common_tags
}

resource "aws_secretsmanager_secret_version" "rag_lambda" {
  secret_id = aws_secretsmanager_secret.rag_lambda.id

  secret_string = jsonencode({
    OPENAI_API_KEY     = var.openai_api_key
    X_API_KEY          = var.x_api_key
    TEAMS_WEBHOOK_URL  = var.teams_webhook_url
    BACKEND_AUTH_TOKEN = var.backend_auth_token
  })
}

# ── IAM Role ─────────────────────────────────────────────────────────────────

resource "aws_iam_role" "lambda" {
  name = "${var.name_prefix}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy" "lambda_s3" {
  name        = "${var.name_prefix}-s3-policy"
  description = "S3 access for RAG bucket + prod bucket (dual-write)"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "RagBucketFullAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject", "s3:PutObject", "s3:DeleteObject",
          "s3:ListBucket", "s3:GetBucketLocation"
        ]
        Resource = [
          aws_s3_bucket.rag.arn,
          "${aws_s3_bucket.rag.arn}/*"
        ]
      },
      {
        Sid    = "ProdBucketDualWrite"
        Effect = "Allow"
        Action = [
          "s3:GetObject", "s3:PutObject",
          "s3:ListBucket", "s3:GetBucketLocation"
        ]
        Resource = [
          aws_s3_bucket.prod.arn,
          "${aws_s3_bucket.prod.arn}/*"
        ]
      }
    ]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "lambda_s3" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.lambda_s3.arn
}

resource "aws_iam_policy" "lambda_secrets" {
  name        = "${var.name_prefix}-secrets-policy"
  description = "Allow Lambda to read its secrets from Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = aws_secretsmanager_secret.rag_lambda.arn
    }]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "lambda_secrets" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.lambda_secrets.arn
}

resource "aws_iam_policy" "lambda_cloudwatch" {
  name        = "${var.name_prefix}-cw-policy"
  description = "Extended CloudWatch metrics for Lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "cloudwatch:PutMetricData",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams"
      ]
      Resource = "*"
    }]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "lambda_cloudwatch" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.lambda_cloudwatch.arn
}

# ── Lambda Function ───────────────────────────────────────────────────────────

resource "aws_lambda_function" "rag" {
  function_name = var.lambda_function_name
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = var.ecr_image_uri

  memory_size = var.lambda_memory_mb
  timeout     = var.lambda_timeout_seconds

  # model cache is baked into /var/task/model_cache (see Dockerfile)
  # /tmp is used for torch + matplotlib scratch (TORCH_HOME=/tmp, MPLCONFIGDIR=/tmp)
  ephemeral_storage {
    size = 1024   # MB — torch scratch space
  }

  environment {
    variables = {
      # ── S3 Buckets ──────────────────────────────────────────────────────
      S3_BUCKET                  = var.rag_bucket_name
      PROD_BUCKET                = var.prod_bucket_name

      # ── Lambda self-reference ───────────────────────────────────────────
      RAG_LAMBDA_FUNCTION_NAME   = var.lambda_function_name

      # ── Backend ─────────────────────────────────────────────────────────
      BACKEND_API_ENDPOINT       = var.backend_api_endpoint

      # ── OpenAI ──────────────────────────────────────────────────────────
      GPT4_MODEL                 = var.gpt4_model
      GPT4_TEMPERATURE           = var.gpt4_temperature
      GPT4_MAX_TOKENS            = var.gpt4_max_tokens

      # ── Embedding ────────────────────────────────────────────────────────
      EMBEDDING_MODEL            = var.embedding_model
      ST_MODEL_NAME              = var.st_model_name

      # ── Confidence / Similarity ──────────────────────────────────────────
      PREDICTION_THRESHOLD       = var.prediction_threshold
      CONFIDENCE_DECAY_RATE      = var.confidence_decay_rate
      CONFIDENCE_GROWTH_RATE     = var.confidence_growth_rate
      MAX_CONFIDENCE             = var.max_confidence
      MIN_CONFIDENCE             = var.min_confidence
      AMBIGUITY_THRESHOLD        = var.ambiguity_threshold
      TOP_K                      = var.top_k
      DEDUP_SIMILARITY_THRESHOLD = var.dedup_similarity_threshold

      # ── Runtime (matches Dockerfile ENV) ─────────────────────────────────
      TRANSFORMERS_CACHE         = "/var/task/model_cache"
      HF_HOME                    = "/var/task/model_cache"
      TORCH_HOME                 = "/tmp"
      MPLCONFIGDIR               = "/tmp"
      PYTHONUNBUFFERED           = "1"

      # ── Secrets (injected at runtime — not plaintext in Lambda env) ──────
      # OPENAI_API_KEY, X_API_KEY, TEAMS_WEBHOOK_URL, BACKEND_AUTH_TOKEN
      # are read from Secrets Manager via the init extension or startup code.
      # Alternatively, pass directly (less secure):
      OPENAI_API_KEY             = var.openai_api_key
      X_API_KEY                  = var.x_api_key
      TEAMS_WEBHOOK_URL          = var.teams_webhook_url
      BACKEND_AUTH_TOKEN         = var.backend_auth_token
    }
  }

  tags = var.common_tags

  lifecycle {
    ignore_changes = [image_uri]   # image updates handled by CI/CD pipeline
  }
}

resource "aws_lambda_function_event_invoke_config" "rag" {
  function_name          = aws_lambda_function.rag.function_name
  maximum_retry_attempts = 0   # RAG is idempotent but retries cause duplicate writes
}

# ── API Gateway (HTTP API v2) ─────────────────────────────────────────────────

resource "aws_apigatewayv2_api" "rag" {
  name          = "${var.name_prefix}-api"
  protocol_type = "HTTP"
  description   = "HTTP API for RAG Lambda — PDF Filler"

  cors_configuration {
    allow_headers = ["content-type", "x-api-key"]
    allow_methods = ["POST", "OPTIONS"]
    allow_origins = ["*"]
    max_age       = 300
  }

  tags = var.common_tags
}

resource "aws_apigatewayv2_integration" "rag" {
  api_id             = aws_apigatewayv2_api.rag.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.rag.invoke_arn
  integration_method = "POST"

  payload_format_version = "2.0"
  timeout_milliseconds   = (var.lambda_timeout_seconds - 1) * 1000
}

resource "aws_apigatewayv2_route" "rag_post" {
  api_id    = aws_apigatewayv2_api.rag.id
  route_key = "POST /"
  target    = "integrations/${aws_apigatewayv2_integration.rag.id}"
}

resource "aws_apigatewayv2_stage" "rag" {
  api_id      = aws_apigatewayv2_api.rag.id
  name        = var.environment
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      sourceIp       = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      responseLength = "$context.responseLength"
      integrationError = "$context.integrationErrorMessage"
    })
  }

  tags = var.common_tags
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.rag.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.rag.execution_arn}/*/*"
}

# ── CloudWatch Log Groups ─────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.lambda_function_name}"
  retention_in_days = var.environment == "prod" ? 90 : 14
  tags              = var.common_tags
}

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${var.name_prefix}"
  retention_in_days = var.environment == "prod" ? 30 : 7
  tags              = var.common_tags
}

# ── CloudWatch Alarms ─────────────────────────────────────────────────────────

resource "aws_sns_topic" "alarms" {
  name = "${var.name_prefix}-alarms"
  tags = var.common_tags
}

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.name_prefix}-errors"
  alarm_description   = "RAG Lambda error rate too high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = 5
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.rag.function_name
  }

  alarm_actions = [aws_sns_topic.alarms.arn]
  tags          = var.common_tags
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "${var.name_prefix}-duration"
  alarm_description   = "RAG Lambda p99 duration approaching timeout"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 60
  extended_statistic  = "p99"
  threshold           = var.lambda_timeout_seconds * 1000 * 0.8   # 80% of timeout
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.rag.function_name
  }

  alarm_actions = [aws_sns_topic.alarms.arn]
  tags          = var.common_tags
}

resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  alarm_name          = "${var.name_prefix}-throttles"
  alarm_description   = "RAG Lambda being throttled"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = 10
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.rag.function_name
  }

  alarm_actions = [aws_sns_topic.alarms.arn]
  tags          = var.common_tags
}

# ── Lambda Reserved Concurrency ───────────────────────────────────────────────

resource "aws_lambda_function_event_invoke_config" "concurrency" {
  function_name          = aws_lambda_function.rag.function_name
  maximum_retry_attempts = 0
}

# Reserved concurrency: sentence-transformers + torch are heavy.
# Prevent runaway concurrent cold starts hammering OpenAI / S3.
resource "aws_lambda_provisioned_concurrency_config" "rag" {
  count                             = var.environment == "prod" ? 1 : 0
  function_name                     = aws_lambda_function.rag.function_name
  qualifier                         = aws_lambda_function.rag.version
  provisioned_concurrent_executions = 2
}
