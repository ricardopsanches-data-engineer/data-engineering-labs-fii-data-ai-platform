output "function_name" {
  description = "Name of the Gold recovery supervisor Lambda function."
  value       = aws_lambda_function.gold_recovery_supervisor.function_name
}

output "function_arn" {
  description = "ARN of the Gold recovery supervisor Lambda function."
  value       = aws_lambda_function.gold_recovery_supervisor.arn
}

output "execution_role_arn" {
  description = "ARN of the Gold recovery supervisor execution role."
  value       = aws_iam_role.lambda_execution.arn
}

output "log_group_name" {
  description = "CloudWatch Logs group for the Gold recovery supervisor Lambda."
  value       = aws_cloudwatch_log_group.lambda.name
}