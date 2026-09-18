output "function_name" {
  description = "Name of the Gold readiness coordinator Lambda function."
  value       = aws_lambda_function.gold_readiness.function_name
}

output "function_arn" {
  description = "ARN of the Gold readiness coordinator Lambda function."
  value       = aws_lambda_function.gold_readiness.arn
}

output "execution_role_arn" {
  description = "ARN of the Gold readiness coordinator execution role."
  value       = aws_iam_role.lambda_execution.arn
}

output "log_group_name" {
  description = "CloudWatch Logs group for the Gold readiness coordinator Lambda."
  value       = aws_cloudwatch_log_group.lambda.name
}