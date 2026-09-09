variable "aws_region" {
  description = "AWS Region used as the home region for the CloudTrail trail."
  type        = string
}

variable "trail_name" {
  description = "Name of the AWS CloudTrail trail."
  type        = string
}

variable "audit_bucket_name" {
  description = "Globally unique S3 bucket used to store CloudTrail audit logs."
  type        = string
}

variable "log_retention_days" {
  description = "Number of days CloudTrail logs are retained in S3."
  type        = number
  default     = 365
}