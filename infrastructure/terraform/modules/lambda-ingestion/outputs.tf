output "function_name" {
  description = "Name of the ingestion Lambda function."
  value       = aws_lambda_function.daily_ingestion.function_name
}

output "function_arn" {
  description = "ARN of the ingestion Lambda function."
  value       = aws_lambda_function.daily_ingestion.arn
}

output "execution_role_arn" {
  description = "ARN of the Lambda execution IAM role."
  value       = aws_iam_role.lambda_execution.arn
}

output "log_group_name" {
  description = "CloudWatch Logs group used by the Lambda function."
  value       = aws_cloudwatch_log_group.lambda.name
}