output "budget_name" {
  description = "Name of the AWS monthly cost budget for the dev environment."
  value       = module.budget.budget_name
}

output "iam_admin_group_name" {
  description = "Name of the IAM group used for Phase 1 platform administration."
  value       = module.iam.admin_group_name
}

output "cloudtrail_name" {
  description = "Name of the CloudTrail trail used for platform audit logging."
  value       = module.observability.trail_name
}

output "cloudtrail_arn" {
  description = "ARN of the CloudTrail trail used for platform audit logging."
  value       = module.observability.trail_arn
}

output "audit_bucket_name" {
  description = "Name of the S3 bucket used to store CloudTrail audit logs."
  value       = module.observability.audit_bucket_name
}

output "audit_bucket_arn" {
  description = "ARN of the S3 bucket used to store CloudTrail audit logs."
  value       = module.observability.audit_bucket_arn
}