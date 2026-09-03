variable "aws_region" {
  description = "AWS region used to deploy resources."
  type        = string
  default     = "sa-east-1"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "dev"
}