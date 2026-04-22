locals {
  # Lambda function name: pdf-autofiller-mapper-dev
  name = "${var.project}-${var.env}"

  # ECR repo was created manually with a different name — allow override via variable.
  # Set ecr_repository_name in terraform.tfvars to "pdf-autofiller-mapper-lambda-dev".
  ecr_name = var.ecr_repository_name != "" ? var.ecr_repository_name : local.name

  # Internal env string the Python code uses for S3 subfolder routing (MAPPER_ENV).
  mapper_env = var.env == "prod" ? "prod_user" : "DEV_user"

  # S3 bucket for hash cache — defaults to main bucket if not overridden.
  cache_bucket = var.pdf_cache_bucket != "" ? var.pdf_cache_bucket : var.s3_bucket
}
