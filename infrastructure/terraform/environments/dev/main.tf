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

module "eventbridge_scheduler" {
  source = "../../modules/eventbridge-scheduler"

  schedule_name = "fii-data-ai-platform-dev-daily-ingestion"

  description = "Triggers the daily FII data ingestion Lambda on business days."

  lambda_function_arn = module.lambda_ingestion.function_arn

  schedule_expression = "cron(0 7 ? * MON-FRI *)"
  schedule_timezone   = "America/Sao_Paulo"

  enabled = true

  maximum_event_age_seconds = 3600
  maximum_retry_attempts    = 2

  tags = {
    Project     = "fii-data-ai-platform"
    Environment = "dev"
    Component   = "DailyIngestionScheduler"
    ManagedBy   = "Terraform"
  }
}

module "cloudwatch_dashboard" {
  source = "../../modules/cloudwatch-dashboard"

  dashboard_name = "fii-data-ai-platform-dev"

  aws_region = var.aws_region

  ingestion_lambda_function_name = (
    module.lambda_ingestion.function_name
  )

  b3_silver_lambda_function_name = (
    module.lambda_b3_silver.function_name
  )
}

module "ecr_b3_silver" {
  source = "../../modules/ecr"

  repository_name = "fii-data-ai-platform-dev-b3-silver"

  lambda_source_arn = "arn:aws:lambda:sa-east-1:625685670804:function:fii-data-ai-platform-dev-b3-raw-to-silver"

  tags = {
    Project     = "fii-data-ai-platform"
    Environment = "dev"
    Component   = "B3Silver"
    ManagedBy   = "Terraform"
  }
}

module "ecr_cvm_silver" {
  source = "../../modules/ecr"

  repository_name = "fii-data-ai-platform-dev-cvm-silver"

  lambda_source_arn = "arn:aws:lambda:sa-east-1:625685670804:function:fii-data-ai-platform-dev-cvm-raw-to-silver"

  tags = {
    Project     = "fii-data-ai-platform"
    Environment = "dev"
    Component   = "CVMSilver"
    ManagedBy   = "Terraform"
  }
}

module "lambda_b3_silver" {
  source = "../../modules/lambda-b3-silver"

  function_name = "fii-data-ai-platform-dev-b3-raw-to-silver"

  image_uri = (
    "${module.ecr_b3_silver.repository_url}:v0.1.3"
  )

  data_lake_bucket_name = module.s3_data_lake.bucket_name
  data_lake_bucket_arn  = module.s3_data_lake.bucket_arn

  timeout     = 120
  memory_size = 1536

  log_retention_days = 14

  tags = {
    Project     = "fii-data-ai-platform"
    Environment = "dev"
    Component   = "B3RawToSilver"
    ManagedBy   = "Terraform"
  }

  depends_on = [
    module.ecr_b3_silver
  ]
}

module "lambda_cvm_silver" {
  source = "../../modules/lambda-cvm-silver"

  function_name = "fii-data-ai-platform-dev-cvm-raw-to-silver"

  image_uri = (
    "${module.ecr_cvm_silver.repository_url}:v0.1.2"
  )

  data_lake_bucket_name = module.s3_data_lake.bucket_name
  data_lake_bucket_arn  = module.s3_data_lake.bucket_arn

  timeout     = 120
  memory_size = 1536

  log_retention_days = 14

  tags = {
    Project     = "fii-data-ai-platform"
    Environment = "dev"
    Component   = "CVMRawToSilver"
    ManagedBy   = "Terraform"
  }

  depends_on = [
    module.ecr_cvm_silver
  ]
}

module "glue_catalog" {
  source = "../../modules/glue-catalog"

  database_name = "fii_data_ai_platform_dev"

  data_lake_bucket_name = module.s3_data_lake.bucket_name

  b3_table_name  = "b3_trades"
  cvm_table_name = "cvm_fund_classes"

  tags = {
    Project     = "fii-data-ai-platform"
    Environment = "dev"
    Component   = "AnalyticsCatalog"
    ManagedBy   = "Terraform"
  }

  depends_on = [
    module.iam
  ]
}

module "athena" {
  source = "../../modules/athena"

  workgroup_name = "fii-data-ai-platform-dev"

  database_name = module.glue_catalog.database_name

  data_lake_bucket_name = module.s3_data_lake.bucket_name
  data_lake_bucket_arn  = module.s3_data_lake.bucket_arn

  query_results_prefix = "athena-results"

  bytes_scanned_cutoff_per_query = 1073741824

  tags = {
    Project     = "fii-data-ai-platform"
    Environment = "dev"
    Component   = "Analytics"
    ManagedBy   = "Terraform"
  }

  depends_on = [
    module.glue_catalog,
    module.iam
  ]
}