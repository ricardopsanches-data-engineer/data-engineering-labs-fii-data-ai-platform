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

variable "tags" {
  description = "Additional tags applied to S3 resources."
  type        = map(string)
  default     = {}
}