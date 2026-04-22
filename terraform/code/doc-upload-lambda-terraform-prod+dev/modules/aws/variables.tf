##############################################################################
# modules/aws/variables.tf
##############################################################################

variable "environment"             { type = string }
variable "aws_region"              { type = string }
variable "name_prefix"             { type = string }
variable "common_tags"             { type = map(string) }

variable "lambda_function_name"    { type = string }
variable "lambda_memory_mb"        { type = number }
variable "lambda_timeout_seconds"  { type = number }

variable "static_bucket_name"      { type = string }
variable "output_bucket_name"      { type = string }
variable "prod_bucket_name"        { type = string }

variable "auth_token"              { type = string; sensitive = true }
variable "openai_api_key"          { type = string; sensitive = true }
variable "pdf_api_key"             { type = string; sensitive = true }
variable "teams_webhook_url"       { type = string; sensitive = true }
variable "admin_password"          { type = string; sensitive = true; default = "" }
variable "admin_username"          { type = string; sensitive = true; default = "" }

variable "fill_pdf_lambda_url"     { type = string; default = "" }
variable "backend_url"             { type = string; default = "" }

##############################################################################
# modules/aws/outputs.tf
##############################################################################

output "lambda_function_name"  { value = aws_lambda_function.extractor.function_name }
output "lambda_function_arn"   { value = aws_lambda_function.extractor.arn }
output "lambda_function_url"   { value = aws_lambda_function_url.extractor.function_url }
output "lambda_role_arn"       { value = aws_iam_role.lambda.arn }
output "static_bucket_name"    { value = aws_s3_bucket.static.bucket }
output "output_bucket_name"    { value = aws_s3_bucket.output.bucket }
output "prod_bucket_name"      { value = aws_s3_bucket.prod.bucket }
output "cloudwatch_log_group"  { value = aws_cloudwatch_log_group.lambda.name }
output "secrets_manager_arn"   { value = aws_secretsmanager_secret.extractor.arn }
output "sns_alarm_topic_arn"   { value = aws_sns_topic.alarms.arn }
