##############################################################################
# modules/aws/outputs.tf
##############################################################################

output "lambda_function_name" { value = aws_lambda_function.rag.function_name }
output "lambda_function_arn"  { value = aws_lambda_function.rag.arn }
output "lambda_role_arn"      { value = aws_iam_role.lambda.arn }
output "rag_bucket_name"      { value = aws_s3_bucket.rag.bucket }
output "prod_bucket_name"     { value = aws_s3_bucket.prod.bucket }
output "ecr_repository_url"   { value = aws_ecr_repository.rag_lambda.repository_url }
output "cloudwatch_log_group" { value = aws_cloudwatch_log_group.lambda.name }
output "api_gateway_url"      { value = aws_apigatewayv2_stage.rag.invoke_url }
output "sns_alarm_topic_arn"  { value = aws_sns_topic.alarms.arn }
output "secrets_manager_arn"  { value = aws_secretsmanager_secret.rag_lambda.arn }
