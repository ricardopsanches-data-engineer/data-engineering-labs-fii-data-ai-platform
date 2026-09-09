output "trail_name" {
  description = "Name of the CloudTrail audit trail."
  value       = aws_cloudtrail.audit.name
}

output "trail_arn" {
  description = "ARN of the CloudTrail audit trail."
  value       = aws_cloudtrail.audit.arn
}

output "audit_bucket_name" {
  description = "Name of the S3 bucket storing CloudTrail audit logs."
  value       = aws_s3_bucket.audit_logs.bucket
}

output "audit_bucket_arn" {
  description = "ARN of the S3 bucket storing CloudTrail audit logs."
  value       = aws_s3_bucket.audit_logs.arn
}