variable "schedule_name" {
  description = "Name of the EventBridge Scheduler schedule."
  type        = string
}

variable "description" {
  description = "Description of the scheduled ingestion job."
  type        = string
  default     = "Triggers the daily FII data ingestion Lambda."
}

variable "lambda_function_arn" {
  description = "ARN of the Lambda function invoked by the schedule."
  type        = string
}

variable "schedule_expression" {
  description = "EventBridge Scheduler cron or rate expression."
  type        = string
  default     = "cron(0 7 ? * MON-FRI *)"
}

variable "schedule_timezone" {
  description = "Timezone used to evaluate the schedule expression."
  type        = string
  default     = "America/Sao_Paulo"
}

variable "enabled" {
  description = "Whether the schedule is enabled."
  type        = bool
  default     = true
}

variable "maximum_event_age_seconds" {
  description = "Maximum age of a failed invocation event before EventBridge stops retrying."
  type        = number
  default     = 3600
}

variable "maximum_retry_attempts" {
  description = "Maximum number of retry attempts for a failed Lambda invocation."
  type        = number
  default     = 2
}

variable "tags" {
  description = "Additional tags applied to the scheduler IAM role."
  type        = map(string)
  default     = {}
}