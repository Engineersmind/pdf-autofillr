locals {
  # Function name: pdf-autofiller-mapper-prod / pdf-autofiller-mapper-dev
  name = "${var.project}-${var.env}"

  # Internal env string the Python code expects (StorageConfig reads MAPPER_ENV)
  mapper_env = var.env == "prod" ? "prod_user" : "DEV_user"

  # S3 bucket for hash cache — defaults to main bucket if not set
  cache_bucket = var.pdf_cache_bucket != "" ? var.pdf_cache_bucket : var.s3_bucket
}
