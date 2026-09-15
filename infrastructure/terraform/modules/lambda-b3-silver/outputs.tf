output "function_name" {
  description = "B3 RAW to Silver Lambda function name."
  value       = aws_lambda_function.b3_raw_to_silver.function_name
}

output "function_arn" {
  description = "B3 RAW to Silver Lambda ARN."
  value       = aws_lambda_function.b3_raw_to_silver.arn
}

output "execution_role_arn" {
  description = "Execution role ARN."
  value       = aws_iam_role.lambda_execution.arn
}

output "log_group_name" {
  description = "CloudWatch log group name."
  value       = aws_cloudwatch_log_group.lambda.name
}