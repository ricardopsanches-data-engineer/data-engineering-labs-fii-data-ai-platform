variable "budget_limit_usd" {
  description = "Monthly AWS budget limit for the dev environment."
  type        = number
  default     = 10
}

variable "budget_notification_email" {
  description = "Email address that receives AWS budget notifications."
  type        = string
}

variable "gold_alert_email" {
  description = "Email address that receives Gold operational alerts."
  type        = string
  sensitive   = true
}

variable "aws_region" {
  description = "AWS region used to deploy resources."
  type        = string
  default     = "sa-east-1"
}