variable "repository_name" {
  description = "Name of the ECR repository."
  type        = string
}

variable "lambda_source_arn" {
  description = "Lambda function ARN allowed to retrieve images from the repository."
  type        = string
}

variable "tags" {
  description = "Tags applied to the ECR repository."
  type        = map(string)
  default     = {}
}