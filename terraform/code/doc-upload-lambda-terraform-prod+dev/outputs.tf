##############################################################################
# outputs.tf
##############################################################################

output "lambda_function_name" {
  value = module.aws.lambda_function_name
}

output "lambda_function_url" {
  description = "Lambda Function URL — used as FILL_PDF_LAMBDA_URL in downstream callers"
  value       = module.aws.lambda_function_url
}

output "lambda_function_arn" {
  value = module.aws.lambda_function_arn
}


output "static_bucket_name" {
  description = "STATIC_BUCKET — schema + session outputs"
  value       = module.aws.static_bucket_name
}

output "output_bucket_name" {
  description = "OUTPUT_BUCKET — flat JSON handoff"
  value       = module.aws.output_bucket_name
}

output "prod_bucket_name" {
  description = "PROD_BUCKET — dual-write mirror"
  value       = module.aws.prod_bucket_name
}

output "cloudwatch_log_group" {
  value = module.aws.cloudwatch_log_group
}

output "lambda_role_arn" {
  value = module.aws.lambda_role_arn
}

output "secrets_manager_arn" {
  value = module.aws.secrets_manager_arn
}

output "sns_alarm_topic_arn" {
  value = module.aws.sns_alarm_topic_arn
}
