variable "aws_account_id" {
  description = "AWS account ID."
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

variable "lambda_function_name" {
  description = "Name of the B3 RAW to Silver Lambda."
  type        = string
}

variable "lambda_function_arn" {
  description = "ARN of the B3 RAW to Silver Lambda."
  type        = string
}

variable "cvm_lambda_function_name" {
  description = "Name of the CVM RAW to Silver Lambda."
  type        = string
}

variable "cvm_lambda_function_arn" {
  description = "ARN of the CVM RAW to Silver Lambda."
  type        = string
}