module "s3_b3_silver_trigger" {
  source = "../../modules/s3-b3-silver-trigger"

  aws_account_id = "625685670804"

  data_lake_bucket_name = module.s3_data_lake.bucket_name
  data_lake_bucket_arn  = module.s3_data_lake.bucket_arn

  lambda_function_name = module.lambda_b3_silver.function_name
  lambda_function_arn  = module.lambda_b3_silver.function_arn

  cvm_lambda_function_name = module.lambda_cvm_silver.function_name
  cvm_lambda_function_arn  = module.lambda_cvm_silver.function_arn

  b3_instruments_lambda_function_name = (
    module.lambda_b3_instruments_silver.function_name
  )

  b3_instruments_lambda_function_arn = (
    module.lambda_b3_instruments_silver.function_arn
  )
}