##############################################################################
# outputs.tf — Key resource identifiers exposed after apply
##############################################################################

output "aws_lambda_function_name" {
  description = "Deployed Lambda function name"
  value       = module.aws.lambda_function_name
}

output "aws_lambda_function_arn" {
  description = "Lambda function ARN"
  value       = module.aws.lambda_function_arn
}

output "aws_api_gateway_url" {
  description = "API Gateway invoke URL"
  value       = module.aws.api_gateway_url
}

output "aws_rag_bucket_name" {
  description = "Primary RAG S3 bucket"
  value       = module.aws.rag_bucket_name
}

output "aws_prod_bucket_name" {
  description = "Production dual-write S3 bucket"
  value       = module.aws.prod_bucket_name
}

output "aws_ecr_repository_url" {
  description = "ECR repository URL for Lambda container images"
  value       = module.aws.ecr_repository_url
}

output "aws_cloudwatch_log_group" {
  description = "CloudWatch log group name for Lambda"
  value       = module.aws.cloudwatch_log_group
}

output "aws_lambda_role_arn" {
  description = "IAM role ARN attached to the Lambda"
  value       = module.aws.lambda_role_arn
}

output "azure_storage_container_url" {
  description = "Azure Blob Storage container URL (if enabled)"
  value       = var.enable_azure ? module.azure[0].storage_container_url : "not deployed"
}

output "gcp_storage_bucket_url" {
  description = "GCP Cloud Storage bucket URL (if enabled)"
  value       = var.enable_gcp ? module.gcp[0].storage_bucket_url : "not deployed"
}
