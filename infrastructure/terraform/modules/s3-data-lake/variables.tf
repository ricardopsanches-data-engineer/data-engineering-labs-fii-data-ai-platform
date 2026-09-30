variable "project_name" {
  description = "Project name used in resource naming and tagging."
  type        = string
}

variable "environment" {
  description = "Deployment environment, such as dev, staging, or prod."
  type        = string
}

variable "bucket_name" {
  description = "Name of the S3 bucket used as the project data lake."
  type        = string
}

variable "force_destroy" {
  description = "Whether Terraform can delete the bucket even if it contains objects."
  type        = bool
  default     = false
}

variable "raw_retention_days" {
  description = "Number of days to retain current RAW objects before expiration."
  type        = number

  validation {
    condition     = var.raw_retention_days >= 1
    error_message = "raw_retention_days must be at least 1."
  }
}

variable "raw_noncurrent_retention_days" {
  description = "Number of days to retain noncurrent versions of RAW objects."
  type        = number

  validation {
    condition     = var.raw_noncurrent_retention_days >= 1
    error_message = "raw_noncurrent_retention_days must be at least 1."
  }
}

variable "incomplete_multipart_retention_days" {
  description = "Number of days before incomplete multipart uploads are aborted."
  type        = number

  validation {
    condition     = var.incomplete_multipart_retention_days >= 1
    error_message = "incomplete_multipart_retention_days must be at least 1."
  }
}

variable "tags" {
  description = "Additional tags applied to S3 resources."
  type        = map(string)
  default     = {}
}