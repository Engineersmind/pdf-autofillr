##############################################################################
# modules/aws/main.tf
#
# Resources:
#   ECR repository
#   S3: static_bucket (schema + per-session outputs + logs)
#   S3: output_bucket (flat JSON handoff)
#   S3: prod_bucket   (dual-write mirror — shared with rag-lambda)
#   Secrets Manager   (all sensitive vars in one secret)
#   IAM role + scoped policies
#   Lambda (container image, Function URL enabled)
#   CloudWatch log groups + metric alarms
#   SNS alarm topic
##############################################################################

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}


# ── S3: static_bucket ─────────────────────────────────────────────────────────
# Stores:
#   config/form_keys.json
#   outputs/{user_id}/sessions/{session_id}/{filled_doc_pdf_id}/
#     final_upload_form_keys_filled.json
#     execution_logs.json

resource "aws_s3_bucket" "static" {
  bucket        = var.static_bucket_name
  force_destroy = var.environment != "prod"
  tags          = var.common_tags
}

resource "aws_s3_bucket_versioning" "static" {
  bucket = aws_s3_bucket.static.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "static" {
  bucket = aws_s3_bucket.static.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_public_access_block" "static" {
  bucket                  = aws_s3_bucket.static.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "static" {
  bucket = aws_s3_bucket.static.id

  # execution_logs.json — incremental flushes + final save by logger_utils.py
  rule {
    id     = "expire-execution-logs"
    status = "Enabled"
    filter { prefix = "outputs/" }
    expiration { days = var.environment == "prod" ? 365 : 90 }
  }

  # config/ — keep forever (schema files)
  rule {
    id     = "retain-config"
    status = "Enabled"
    filter { prefix = "config/" }
    noncurrent_version_expiration { noncurrent_days = 30 }
  }
}

# ── S3: output_bucket ─────────────────────────────────────────────────────────
# Stores flat JSON handoff:
#   {user_id}/sessions/{session_id}/final_output_flat.json

resource "aws_s3_bucket" "output" {
  bucket        = var.output_bucket_name
  force_destroy = var.environment != "prod"
  tags          = merge(var.common_tags, { Role = "flat-json-handoff" })
}

resource "aws_s3_bucket_versioning" "output" {
  bucket = aws_s3_bucket.output.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "output" {
  bucket = aws_s3_bucket.output.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_public_access_block" "output" {
  bucket                  = aws_s3_bucket.output.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "output" {
  bucket = aws_s3_bucket.output.id

  rule {
    id     = "expire-flat-outputs"
    status = "Enabled"
    filter { prefix = "" }
    expiration { days = var.environment == "prod" ? 365 : 90 }
  }
}

# ── S3: prod_bucket ───────────────────────────────────────────────────────────
# PROD_BUCKET — shared dual-write mirror (logger_utils.py + s3_handler.py)
# Path patterns:
#   {env}/{user_type}/{user_id}/sessions/{session_id}/doc_upload/{filled_doc_pdf_id}/
#     final_upload_form_keys_filled.json
#     execution_logs.json
#   {env}/{user_type}/{user_id}/sessions/{session_id}/final_output_flat.json
#
# NOTE: This bucket is also written to by rag-lambda.
# If rag-lambda Terraform already manages it, import it here instead:
#   terraform import module.aws.aws_s3_bucket.prod pdf-fillr-production

resource "aws_s3_bucket" "prod" {
  bucket        = var.prod_bucket_name
  force_destroy = false   # never auto-destroy — shared prod asset
  tags          = merge(var.common_tags, { Role = "dual-write-mirror", Shared = "true" })
}

resource "aws_s3_bucket_versioning" "prod" {
  bucket = aws_s3_bucket.prod.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "prod" {
  bucket = aws_s3_bucket.prod.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
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

  rule {
    id     = "expire-dev-session-data"
    status = "Enabled"
    filter { prefix = "dev/" }
    expiration { days = 90 }
  }

  rule {
    id     = "expire-local-session-data"
    status = "Enabled"
    filter { prefix = "local/" }
    expiration { days = 30 }
  }

  rule {
    id     = "retain-prod-session-data"
    status = "Enabled"
    filter { prefix = "prod/" }
    expiration { days = 365 }
  }
}

# ── Secrets Manager ───────────────────────────────────────────────────────────
# All sensitive vars from .env in a single secret

resource "aws_secretsmanager_secret" "extractor" {
  name                    = "${var.name_prefix}/env"
  description             = "All sensitive env vars for ${var.name_prefix} Lambda"
  recovery_window_in_days = var.environment == "prod" ? 30 : 0
  tags                    = var.common_tags
}

resource "aws_secretsmanager_secret_version" "extractor" {
  secret_id = aws_secretsmanager_secret.extractor.id

  secret_string = jsonencode({
    AUTH_TOKEN        = var.auth_token
    OPENAI_API_KEY    = var.openai_api_key
    PDF_API_KEY       = var.pdf_api_key
    TEAMS_WEBHOOK_URL = var.teams_webhook_url
    ADMIN_PASSWORD    = var.admin_password
    ADMIN_USERNAME    = var.admin_username
  })
}

# ── IAM Role ──────────────────────────────────────────────────────────────────

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

resource "aws_iam_role_policy_attachment" "basic_execution" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy" "s3_access" {
  name        = "${var.name_prefix}-s3"
  description = "S3 access for static_bucket, output_bucket, prod_bucket (dual-write)"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # STATIC_BUCKET — full access (schema read, output write, log flush)
        Sid    = "StaticBucketAccess"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject",
                  "s3:ListBucket", "s3:GetBucketLocation"]
        Resource = [
          aws_s3_bucket.static.arn,
          "${aws_s3_bucket.static.arn}/*"
        ]
      },
      {
        # OUTPUT_BUCKET — write flat JSON, read for verification
        Sid    = "OutputBucketAccess"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject",
                  "s3:ListBucket", "s3:GetBucketLocation"]
        Resource = [
          aws_s3_bucket.output.arn,
          "${aws_s3_bucket.output.arn}/*"
        ]
      },
      {
        # PROD_BUCKET — write only (dual-write, silent fail on error)
        # s3_handler.py and logger_utils.py both write here
        Sid    = "ProdBucketDualWrite"
        Effect = "Allow"
        Action = ["s3:PutObject", "s3:GetObject",
                  "s3:ListBucket", "s3:GetBucketLocation"]
        Resource = [
          aws_s3_bucket.prod.arn,
          "${aws_s3_bucket.prod.arn}/*"
        ]
      },
      {
        # Source PDFs may live in any bucket — allow GetObject on *
        # Narrow this down if you know the source bucket(s)
        Sid      = "SourcePDFRead"
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = ["arn:aws:s3:::*/*"]
      }
    ]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "s3_access" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.s3_access.arn
}

resource "aws_iam_policy" "secrets_access" {
  name        = "${var.name_prefix}-secrets"
  description = "Read Secrets Manager secret"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = aws_secretsmanager_secret.extractor.arn
    }]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "secrets_access" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.secrets_access.arn
}

resource "aws_iam_policy" "cloudwatch_access" {
  name = "${var.name_prefix}-cloudwatch"

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

resource "aws_iam_role_policy_attachment" "cloudwatch_access" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.cloudwatch_access.arn
}

# ── Lambda Function ───────────────────────────────────────────────────────────

resource "aws_lambda_function" "extractor" {
  function_name = var.lambda_function_name
  role          = aws_iam_role.lambda.arn
  package_type     = "Zip"
  filename         = "${path.module}/lambda.zip"
  source_code_hash = filebase64sha256("${path.module}/lambda.zip")
  runtime          = "python3.12"
  handler          = "lambda_function.handler"

  memory_size = var.lambda_memory_mb
  timeout     = var.lambda_timeout_seconds

  # Thread B polls up to 480s; fill_pdf is 200s — total can hit ~500s + overhead
  # /tmp: PyMuPDF writes temporary rasterisation files
  ephemeral_storage {
    size = 1024
  }

  environment {
    variables = {
      # ── S3 ───────────────────────────────────────────────────────────────
      STATIC_BUCKET = var.static_bucket_name
      OUTPUT_BUCKET = var.output_bucket_name
      PROD_BUCKET   = var.prod_bucket_name

      # ── Downstream fill-pdf Lambda ────────────────────────────────────────
      FILL_PDF_LAMBDA_URL = var.fill_pdf_lambda_url

      # ── Backend ───────────────────────────────────────────────────────────
      BACKEND_URL = var.backend_url

      # ── Secrets (injected directly; swap to SM fetch for hardened prod) ───
      AUTH_TOKEN        = var.auth_token
      OPENAI_API_KEY    = var.openai_api_key
      PDF_API_KEY       = var.pdf_api_key
      TEAMS_WEBHOOK_URL = var.teams_webhook_url
      ADMIN_PASSWORD    = var.admin_password
      ADMIN_USERNAME    = var.admin_username

      # ── Runtime ───────────────────────────────────────────────────────────
      PYTHONUNBUFFERED = "1"
    }
  }

  tags = var.common_tags

}

# ── Lambda Function URL (replaces API Gateway — matches existing setup) ────────
# lambda_function.py uses "body" + "headers" keys from event — Lambda URL provides these

resource "aws_lambda_function_url" "extractor" {
  function_name      = aws_lambda_function.extractor.function_name
  authorization_type = "NONE"   # Auth handled in-code: AUTH_TOKEN header check

  cors {
    allow_credentials = false
    allow_headers     = ["content-type", "x-api-key"]
    allow_methods     = ["POST"]
    allow_origins     = ["*"]
    max_age           = 300
  }
}

# No retry — parallel threads are stateful (embed file polling); retries cause side effects
resource "aws_lambda_function_event_invoke_config" "extractor" {
  function_name          = aws_lambda_function.extractor.function_name
  maximum_retry_attempts = 0
}

# ── CloudWatch Log Groups ─────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.lambda_function_name}"
  retention_in_days = var.environment == "prod" ? 90 : 14
  tags              = var.common_tags
}

# ── SNS Alarm Topic ───────────────────────────────────────────────────────────

resource "aws_sns_topic" "alarms" {
  name = "${var.name_prefix}-alarms"
  tags = var.common_tags
}

# ── CloudWatch Alarms ─────────────────────────────────────────────────────────

resource "aws_cloudwatch_metric_alarm" "errors" {
  alarm_name          = "${var.name_prefix}-errors"
  alarm_description   = "Doc Upload Lambda error rate high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = 3
  treat_missing_data  = "notBreaching"
  dimensions          = { FunctionName = aws_lambda_function.extractor.function_name }
  alarm_actions       = [aws_sns_topic.alarms.arn]
  tags                = var.common_tags
}

resource "aws_cloudwatch_metric_alarm" "duration" {
  alarm_name          = "${var.name_prefix}-duration"
  alarm_description   = "Doc Upload Lambda nearing timeout (parallel threads can run 500s+)"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 60
  extended_statistic  = "p95"
  # Alert at 80% of timeout — Thread B can legitimately take ~480s
  threshold           = var.lambda_timeout_seconds * 1000 * 0.8
  treat_missing_data  = "notBreaching"
  dimensions          = { FunctionName = aws_lambda_function.extractor.function_name }
  alarm_actions       = [aws_sns_topic.alarms.arn]
  tags                = var.common_tags
}

resource "aws_cloudwatch_metric_alarm" "throttles" {
  alarm_name          = "${var.name_prefix}-throttles"
  alarm_description   = "Doc Upload Lambda being throttled"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = 5
  treat_missing_data  = "notBreaching"
  dimensions          = { FunctionName = aws_lambda_function.extractor.function_name }
  alarm_actions       = [aws_sns_topic.alarms.arn]
  tags                = var.common_tags
}

# ── CloudWatch Log Metric Filter: Teams notify failures ───────────────────────
# Catches "[Teams] Failure notification sent" — lets you track failure rate

resource "aws_cloudwatch_log_metric_filter" "teams_failures" {
  name           = "${var.name_prefix}-teams-failures"
  log_group_name = aws_cloudwatch_log_group.lambda.name
  pattern        = "\"[Teams] Failure notification sent\""

  metric_transformation {
    name      = "TeamsPipelineFailures"
    namespace = "DocUpload/${var.environment}"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "teams_failures" {
  alarm_name          = "${var.name_prefix}-pipeline-failures"
  alarm_description   = "PDF pipeline failures (Teams notifications sent)"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "TeamsPipelineFailures"
  namespace           = "DocUpload/${var.environment}"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  tags                = var.common_tags
}

# ── Provisioned Concurrency (prod only) ───────────────────────────────────────
# PyMuPDF + dependencies cold start is slow — warm 1 instance in prod

resource "aws_lambda_provisioned_concurrency_config" "extractor" {
  count                             = var.environment == "prod" ? 1 : 0
  function_name                     = aws_lambda_function.extractor.function_name
  qualifier                         = aws_lambda_function.extractor.version
  provisioned_concurrent_executions = 1
}
