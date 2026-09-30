variable "log_group_name" {
  description = "CloudWatch Log Group containing structured Gold operational events."
  type        = string
}

variable "metric_namespace" {
  description = "CloudWatch namespace used for Gold operational metrics."
  type        = string
  default     = "FiiDataAiPlatform/Gold"
}

variable "operational_error_metric_name" {
  description = "CloudWatch metric name for Gold operational ERROR events."
  type        = string
  default     = "OperationalErrors"
}

variable "alarm_name" {
  description = "CloudWatch alarm name for Gold operational errors."
  type        = string
}

variable "alarm_description" {
  description = "Description shown in the CloudWatch alarm."
  type        = string
  default     = "Gold operational ERROR event detected."
}

variable "alarm_period_seconds" {
  description = "CloudWatch alarm evaluation period in seconds."
  type        = number
  default     = 300

  validation {
    condition     = var.alarm_period_seconds >= 60
    error_message = "alarm_period_seconds must be at least 60 seconds."
  }
}

variable "alarm_evaluation_periods" {
  description = "Number of periods evaluated by the Gold operational alarm."
  type        = number
  default     = 1

  validation {
    condition     = var.alarm_evaluation_periods >= 1
    error_message = "alarm_evaluation_periods must be at least 1."
  }
}

variable "alarm_threshold" {
  description = "Number of Gold operational ERROR events required to enter ALARM."
  type        = number
  default     = 1

  validation {
    condition     = var.alarm_threshold >= 1
    error_message = "alarm_threshold must be at least 1."
  }
}

variable "sns_topic_name" {
  description = "SNS topic used to deliver Gold operational alerts."
  type        = string
}

variable "alert_email" {
  description = "Email address subscribed to Gold operational alerts."
  type        = string

  validation {
    condition = (
      length(trimspace(var.alert_email)) > 3
      && can(regex("@", var.alert_email))
    )

    error_message = "alert_email must contain a valid email address."
  }
}

variable "tags" {
  description = "Tags applied to supported Gold operational observability resources."
  type        = map(string)
  default     = {}
}