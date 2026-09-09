variable "aws_region" {
  description = "AWS region used for the Terraform backend."
  type        = string
  default     = "sa-east-1"
}

variable "state_bucket_name" {
  description = "Globally unique S3 bucket name used to store Terraform state."
  type        = string
  default     = "fii-data-ai-platform-tfstate-625685670804"
}