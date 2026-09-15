variable "dashboard_name" {
  description = "Name of the CloudWatch dashboard."
  type        = string
}

variable "aws_region" {
  description = "AWS region used by the dashboard widgets."
  type        = string
}

variable "ingestion_lambda_function_name" {
  description = "Daily ingestion Lambda function monitored by the dashboard."
  type        = string
}

variable "b3_silver_lambda_function_name" {
  description = "B3 RAW to Silver Lambda function monitored by the dashboard."
  type        = string
}