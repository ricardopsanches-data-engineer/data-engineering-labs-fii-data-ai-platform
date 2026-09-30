variable "schedule_name_prefix" {
  description = "Prefix used for Gold recovery watchdog schedule names."
  type        = string
}


variable "supervisor_lambda_arn" {
  description = "ARN of the Gold recovery supervisor Lambda invoked by the watchdog."
  type        = string
}


variable "checks" {
  description = "Gold recovery watchdog checks keyed by logical schedule name."

  type = map(object({
    hour              = number
    attempt           = number
    max_attempts      = number
    final_attempt     = bool
    verification_only = bool
  }))

  default = {
    "attempt-1" = {
      hour              = 10
      attempt           = 1
      max_attempts      = 3
      final_attempt     = false
      verification_only = false
    }

    "attempt-2" = {
      hour              = 14
      attempt           = 2
      max_attempts      = 3
      final_attempt     = false
      verification_only = false
    }

    "attempt-3" = {
      hour              = 18
      attempt           = 3
      max_attempts      = 3
      final_attempt     = true
      verification_only = false
    }

    "verify" = {
      hour              = 20
      attempt           = 3
      max_attempts      = 3
      final_attempt     = true
      verification_only = true
    }
  }

  validation {
    condition = alltrue([
      for check in values(var.checks) :
      check.hour >= 0 &&
      check.hour <= 23
    ])

    error_message = "Each watchdog check hour must be between 0 and 23."
  }

  validation {
    condition = alltrue([
      for check in values(var.checks) :
      check.attempt >= 1 &&
      check.max_attempts >= 1 &&
      check.attempt <= check.max_attempts
    ])

    error_message = "Each watchdog check must use a valid attempt between 1 and max_attempts."
  }
}


variable "lookback_days" {
  description = "Recovery lookback window used by each watchdog check."
  type        = number
  default     = 1

  validation {
    condition     = var.lookback_days >= 1
    error_message = "lookback_days must be greater than or equal to 1."
  }
}


variable "schedule_timezone" {
  description = "Timezone used by the Gold recovery watchdog schedules."
  type        = string
  default     = "America/Sao_Paulo"
}


variable "enabled" {
  description = "Whether the Gold recovery watchdog schedules are enabled."
  type        = bool
  default     = true
}


variable "maximum_event_age_seconds" {
  description = "Maximum age in seconds for a watchdog Scheduler delivery."
  type        = number
  default     = 3600

  validation {
    condition = (
      var.maximum_event_age_seconds >= 60 &&
      var.maximum_event_age_seconds <= 86400
    )

    error_message = "maximum_event_age_seconds must be between 60 and 86400."
  }
}


variable "maximum_retry_attempts" {
  description = "Scheduler transport-level retry attempts. Business recovery attempts are modeled separately."
  type        = number
  default     = 0

  validation {
    condition = (
      var.maximum_retry_attempts >= 0 &&
      var.maximum_retry_attempts <= 185
    )

    error_message = "maximum_retry_attempts must be between 0 and 185."
  }
}


variable "tags" {
  description = "Additional tags applied to watchdog IAM resources."
  type        = map(string)
  default     = {}
}