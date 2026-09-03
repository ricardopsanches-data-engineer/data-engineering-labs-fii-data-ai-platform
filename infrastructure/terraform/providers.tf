provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "fii-data-ai-platform"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}