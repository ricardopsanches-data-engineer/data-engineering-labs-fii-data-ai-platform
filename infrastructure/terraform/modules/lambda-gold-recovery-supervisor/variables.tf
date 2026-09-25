variable "function_name" {
  description = "Name of the Gold recovery supervisor Lambda function."
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
  default     = "src.orchestration.gold_recovery_supervisor.lambda_handler"
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
  description = "Name of the S3 data lake bucket used by the Gold recovery supervisor."
  type        = string
}

variable "data_lake_bucket_arn" {
  description = "ARN of the S3 data lake bucket used by the Gold recovery supervisor."
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

variable "raw_to_silver_function_names" {
  description = "Map of RAW-to-Silver Lambda function names keyed by recovery source."
  type        = map(string)
}

variable "raw_to_silver_function_arns" {
  description = "Map of RAW-to-Silver Lambda function ARNs keyed by recovery source."
  type        = map(string)
}

variable "lookback_days" {
  description = "Operational recovery lookback window in days."
  type        = number
  default     = 30

  validation {
    condition     = var.lookback_days >= 1
    error_message = "lookback_days must be greater than or equal to 1."
  }
}

variable "expected_weekdays" {
  description = "Expected operational weekdays using Python weekday numbering, where Monday is 0 and Sunday is 6."
  type        = list(number)

  default = [
    0,
    1,
    2,
    3,
    4,
  ]

  validation {
    condition = alltrue([
      for weekday in var.expected_weekdays :
      weekday >= 0 && weekday <= 6
    ])

    error_message = "expected_weekdays values must be between 0 and 6."
  }
}

variable "excluded_dates" {
  description = "Explicit ISO dates excluded from expected recovery cycles."
  type        = list(string)
  default     = []
}

variable "timeout" {
  description = "Maximum Lambda execution time in seconds."
  type        = number
  default     = 60
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