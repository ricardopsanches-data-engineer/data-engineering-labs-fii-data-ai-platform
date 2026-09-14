module "budget" {
  source = "../../modules/budget"

  budget_name        = "fii-data-ai-platform-dev-monthly"
  limit_amount       = var.budget_limit_usd
  notification_email = var.budget_notification_email
}

module "iam" {
  source = "../../modules/iam"

  admin_group_name = "fii-platform-admins"
  admin_user_name  = "fii-platform-admin"
}

module "observability" {
  source = "../../modules/observability"

  aws_region         = var.aws_region
  trail_name         = "fii-data-ai-platform-dev"
  audit_bucket_name  = "fii-data-ai-platform-audit-625685670804"
  log_retention_days = 365
}

module "s3_data_lake" {
  source = "../../modules/s3-data-lake"

  project_name = "fii-data-ai-platform"
  environment  = "dev"

  bucket_name = "fii-data-ai-platform-dev-datalake-625685670804"

  force_destroy = false

  tags = {
    Owner = "DataEngineering"
    Layer = "DataLake"
  }
}

module "lambda_ingestion" {
  source = "../../modules/lambda-ingestion"

  function_name = "fii-data-ai-platform-dev-daily-ingestion"

  filename = "../../../../lambda/daily-ingestion/build/daily_ingestion.zip"

  source_code_hash = filebase64sha256(
    "../../../../lambda/daily-ingestion/build/daily_ingestion.zip"
  )

  data_lake_bucket_name = module.s3_data_lake.bucket_name
  data_lake_bucket_arn  = module.s3_data_lake.bucket_arn

  timeout     = 60
  memory_size = 512

  log_retention_days = 14

  tags = {
    Project     = "fii-data-ai-platform"
    Environment = "dev"
    Component   = "DailyIngestion"
    ManagedBy   = "Terraform"
  }
}