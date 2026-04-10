output "function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.mapper.function_name
}

output "function_url" {
  description = "Lambda Function URL — use this as the mapper endpoint"
  value       = aws_lambda_function_url.mapper.function_url
}

output "ecr_repository_url" {
  description = "ECR repository URL — used by deploy.sh to tag and push images"
  value       = aws_ecr_repository.mapper.repository_url
}

output "log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.mapper.name
}
