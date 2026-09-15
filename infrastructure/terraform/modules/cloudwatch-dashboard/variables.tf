variable "dashboard_name" {
  description = "Name of the CloudWatch dashboard."
  type        = string
}

variable "aws_region" {
  description = "AWS region used by the dashboard widgets."
  type        = string
}

variable "lambda_function_name" {
  description = "Lambda function monitored by the dashboard."
  type        = string
}