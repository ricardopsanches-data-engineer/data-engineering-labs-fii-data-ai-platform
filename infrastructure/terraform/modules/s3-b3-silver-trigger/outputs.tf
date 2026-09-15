output "lambda_permission_statement_id" {
  description = "Statement ID allowing S3 to invoke the Lambda."
  value       = aws_lambda_permission.allow_s3.statement_id
}

output "bucket_notification_id" {
  description = "S3 bucket notification resource ID."
  value       = aws_s3_bucket_notification.b3_raw_to_silver.id
}