output "function_name" {
  description = "FII Master Gold Lambda function name."
  value       = aws_lambda_function.fii_master_gold.function_name
}


output "function_arn" {
  description = "FII Master Gold Lambda function ARN."
  value       = aws_lambda_function.fii_master_gold.arn
}


output "execution_role_arn" {
  description = "FII Master Gold Lambda execution role ARN."
  value       = aws_iam_role.lambda_execution.arn
}