# ---------------------------------------------------------------------------
# IAM — Lambda execution role and permission policy
#
# Both S3 buckets already exist — we only grant permissions, not create them.
# ---------------------------------------------------------------------------

resource "aws_iam_role" "lambda" {
  name = "${local.name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_permissions" {
  name = "${local.name}-permissions"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # Full access to main pipeline bucket (session data, mapper outputs, rag subfolder)
        # Path shape: {env}/{user_type}/{user_id}/sessions/{session_id}/rag/{pdf_id}/...
        Sid    = "S3MainBucket"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:HeadObject",
        ]
        Resource = [
          "arn:aws:s3:::${var.s3_bucket}",
          "arn:aws:s3:::${var.s3_bucket}/*",
        ]
      },
      {
        # Read-only access to the uploads bucket where the chatbot stores raw PDFs.
        # The mapper fetches the PDF via its S3 URL returned by the backend API.
        Sid    = "S3UploadsBucketRead"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:HeadObject",
        ]
        Resource = [
          "arn:aws:s3:::${var.uploads_bucket}",
          "arn:aws:s3:::${var.uploads_bucket}/*",
        ]
      },
      {
        # Scoped write to rag-bucket-pdf-filler — mapper only touches:
        #   predictions/{user_id}/{session_id}/{pdf_id}/input_file/header_file.json  (upload before RAG API call)
        #   predictions/{user_id}/{session_id}/{pdf_id}/llm_predictions.json
        #   predictions/{user_id}/{session_id}/{pdf_id}/final_predictions.json
        #   predictions/{user_id}/{session_id}/{pdf_id}/rag_predictions.json         (read-back after RAG API writes it)
        Sid    = "S3RagBucketPredictions"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:HeadObject",
          "s3:ListBucket",
        ]
        Resource = [
          "arn:aws:s3:::${var.rag_bucket}",
          "arn:aws:s3:::${var.rag_bucket}/predictions/*",
        ]
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${local.name}:*"
      },
     {
        Sid    = "BedrockInvokeModel"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
        ]
        Resource = [
          "arn:aws:bedrock:*::foundation-model/*",
          "arn:aws:bedrock:*:${data.aws_caller_identity.current.account_id}:inference-profile/*",
          "arn:aws:bedrock:*:${data.aws_caller_identity.current.account_id}:application-inference-profile/*"
        ]
      },
      {
        Sid    = "AWSMarketplaceSubscription"
        Effect = "Allow"
        Action = [
          "aws-marketplace:ViewSubscriptions",
          "aws-marketplace:Subscribe"
        ]
        Resource = "*"
      },
    ]
  })
}

# ── rag_bucket variable ───────────────────────────────────────────────────────
variable "rag_bucket" {
  description = "RAG S3 bucket name (mapper writes header_file + predictions here)"
  type        = string
  default     = "rag-bucket-pdf-filler"
}

variable "uploads_bucket" {
  description = "S3 bucket where the chatbot/backend uploads raw PDFs (mapper needs read access)"
  type        = string
  default     = "pdf-autofiller-dev"
}
