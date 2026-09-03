variable "budget_name" {
  description = "Name of the AWS monthly cost budget."
  type        = string
}

variable "limit_amount" {
  description = "Monthly budget limit in USD."
  type        = number
}

variable "notification_email" {
  description = "Email address that receives budget alerts."
  type        = string
}