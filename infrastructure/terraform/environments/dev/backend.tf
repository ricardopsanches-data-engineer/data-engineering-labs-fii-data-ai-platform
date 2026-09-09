terraform {
  backend "s3" {
    bucket       = "fii-data-ai-platform-tfstate-625685670804"
    key          = "environments/dev/terraform.tfstate"
    region       = "sa-east-1"
    encrypt      = true
    use_lockfile = true
  }
}