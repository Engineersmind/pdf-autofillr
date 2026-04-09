terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  # Uncomment to use S3 backend for shared state:
  # backend "s3" {
  #   bucket = "your-tfstate-bucket"
  #   key    = "mapper/${var.env}/terraform.tfstate"
  #   region = var.region
  # }
}

provider "aws" {
  region = var.region
}

locals {
  name   = "pdf-autofillr-mapper-${var.env}"
  tags   = { Project = "pdf-autofillr", Module = "mapper", Env = var.env }
}

# ── Secrets (API keys stored in SSM, not in Terraform state) ─────────────────
resource "aws_ssm_parameter" "llm_api_key" {
  name  = "/${local.name}/LLM_API_KEY"
  type  = "SecureString"
  value = "REPLACE_ME"   # Set manually: aws ssm put-parameter --name ... --value <key>
  lifecycle { ignore_changes = [value] }
  tags  = local.tags
}

# ── IAM Role for Lambda ───────────────────────────────────────────────────────
resource "aws_iam_role" "lambda" {
  count = var.deploy_mode == "lambda" ? 1 : 0
  name  = "${local.name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  count      = var.deploy_mode == "lambda" ? 1 : 0
  role       = aws_iam_role.lambda[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_s3_ssm" {
  count = var.deploy_mode == "lambda" ? 1 : 0
  name  = "s3-ssm-access"
  role  = aws_iam_role.lambda[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
        Resource = ["arn:aws:s3:::*"]   # Tighten to specific bucket in prod
      },
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter", "ssm:GetParameters"]
        Resource = ["arn:aws:ssm:${var.region}:*:parameter/${local.name}/*"]
      }
    ]
  })
}

# ── Lambda Function ───────────────────────────────────────────────────────────
resource "aws_lambda_function" "mapper" {
  count         = var.deploy_mode == "lambda" ? 1 : 0
  function_name = local.name
  role          = aws_iam_role.lambda[0].arn
  package_type  = "Image"
  image_uri     = var.image_uri
  memory_size   = var.lambda_memory_mb
  timeout       = var.lambda_timeout_sec

  environment {
    variables = {
      DEPLOY_MODE   = "lambda"
      LLM_MODEL     = var.llm_model
      RAG_API_URL   = var.rag_api_url
      LOG_LEVEL     = "INFO"
      # LLM_API_KEY loaded from SSM at runtime via entrypoint
    }
  }

  tags = local.tags
}

# ── API Gateway (HTTP API) ────────────────────────────────────────────────────
resource "aws_apigatewayv2_api" "mapper" {
  count         = var.deploy_mode == "lambda" ? 1 : 0
  name          = local.name
  protocol_type = "HTTP"
  tags          = local.tags
}

resource "aws_apigatewayv2_integration" "mapper" {
  count              = var.deploy_mode == "lambda" ? 1 : 0
  api_id             = aws_apigatewayv2_api.mapper[0].id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.mapper[0].invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "mapper" {
  count     = var.deploy_mode == "lambda" ? 1 : 0
  api_id    = aws_apigatewayv2_api.mapper[0].id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.mapper[0].id}"
}

resource "aws_apigatewayv2_stage" "mapper" {
  count       = var.deploy_mode == "lambda" ? 1 : 0
  api_id      = aws_apigatewayv2_api.mapper[0].id
  name        = "$default"
  auto_deploy = true
  tags        = local.tags
}

resource "aws_lambda_permission" "apigw" {
  count         = var.deploy_mode == "lambda" ? 1 : 0
  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.mapper[0].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.mapper[0].execution_arn}/*/*"
}
