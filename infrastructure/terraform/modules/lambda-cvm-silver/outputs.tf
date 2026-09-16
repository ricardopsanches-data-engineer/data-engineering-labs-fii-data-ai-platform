output "function_name" {
  description = "Name of the CVM RAW to Silver Lambda."
  value       = aws_lambda_function.cvm_raw_to_silver.function_name
}

output "function_arn" {
  description = "ARN of the CVM RAW to Silver Lambda."
  value       = aws_lambda_function.cvm_raw_to_silver.arn
}