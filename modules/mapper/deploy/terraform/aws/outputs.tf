output "api_url" {
  description = "API Gateway endpoint URL"
  value       = var.deploy_mode == "lambda" ? aws_apigatewayv2_stage.mapper[0].invoke_url : ""
}

output "lambda_function_name" {
  value = var.deploy_mode == "lambda" ? aws_lambda_function.mapper[0].function_name : ""
}
