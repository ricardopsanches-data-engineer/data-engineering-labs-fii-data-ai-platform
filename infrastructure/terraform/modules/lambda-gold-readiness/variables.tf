variable "function_name" {
  description = "Name of the Gold readiness coordinator Lambda function."
  type        = string
}

variable "runtime" {
  description = "Lambda Python runtime."
  type        = string
  default     = "python3.12"
}

variable "handler" {
  description = "Lambda handler entry point."
  type        = string
  default     = "src.orchestration.gold_readiness_coordinator.lambda_handler"
}

variable "filename" {
  description = "Path to the Lambda deployment ZIP file."
  type        = string
}

variable "source_code_hash" {
  description = "Base64-encoded SHA256 hash of the Lambda deployment package."
  type        = string
}

variable "data_lake_bucket_name" {
  description = "Name of the S3 data lake bucket used by the readiness coordinator."
  type        = string
}

variable "data_lake_bucket_arn" {
  description = "ARN of the S3 data lake bucket used by the readiness coordinator."
  type        = string
}

variable "gold_lambda_function_name" {
  description = "Name of the Gold FII master Lambda function."
  type        = string
}

variable "gold_lambda_function_arn" {
  description = "ARN of the Gold FII master Lambda function."
  type        = string
}

variable "timeout" {
  description = "Maximum Lambda execution time in seconds."
  type        = number
  default     = 30
}

variable "memory_size" {
  description = "Lambda memory size in MB."
  type        = number
  default     = 128
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention period in days."
  type        = number
  default     = 14
}

variable "tags" {
  description = "Additional tags applied to Lambda resources."
  type        = map(string)
  default     = {}
}