variable "function_name" {
  description = "Name of the B3 Instruments RAW to Silver Lambda."
  type        = string
}

variable "image_uri" {
  description = "ECR image URI used by the Lambda."
  type        = string
}

variable "data_lake_bucket_name" {
  description = "Name of the data lake S3 bucket."
  type        = string
}

variable "data_lake_bucket_arn" {
  description = "ARN of the data lake S3 bucket."
  type        = string
}

variable "timeout" {
  description = "Lambda timeout in seconds."
  type        = number
  default     = 180
}

variable "memory_size" {
  description = "Lambda memory size in MB."
  type        = number
  default     = 2048
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention in days."
  type        = number
  default     = 14
}

variable "tags" {
  description = "Tags applied to Lambda resources."
  type        = map(string)
  default     = {}
}