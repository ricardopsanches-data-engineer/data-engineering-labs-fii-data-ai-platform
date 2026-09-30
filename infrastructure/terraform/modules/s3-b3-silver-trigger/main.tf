resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3InvokeB3RawToSilver"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "s3.amazonaws.com"

  source_arn     = var.data_lake_bucket_arn
  source_account = var.aws_account_id
}

resource "aws_lambda_permission" "allow_s3_cvm" {
  statement_id  = "AllowS3InvokeCVMRawToSilver"
  action        = "lambda:InvokeFunction"
  function_name = var.cvm_lambda_function_name
  principal     = "s3.amazonaws.com"

  source_arn     = var.data_lake_bucket_arn
  source_account = var.aws_account_id
}

resource "aws_lambda_permission" "allow_s3_b3_instruments" {
  statement_id  = "AllowS3InvokeB3InstrumentsRawToSilver"
  action        = "lambda:InvokeFunction"
  function_name = var.b3_instruments_lambda_function_name
  principal     = "s3.amazonaws.com"

  source_arn     = var.data_lake_bucket_arn
  source_account = var.aws_account_id
}

resource "aws_lambda_permission" "allow_s3_gold_readiness" {
  statement_id  = "AllowS3InvokeGoldReadiness"
  action        = "lambda:InvokeFunction"
  function_name = var.gold_readiness_lambda_function_name
  principal     = "s3.amazonaws.com"

  source_arn     = var.data_lake_bucket_arn
  source_account = var.aws_account_id
}

resource "aws_s3_bucket_notification" "b3_raw_to_silver" {
  bucket = var.data_lake_bucket_name

  lambda_function {
    lambda_function_arn = var.lambda_function_arn

    events = [
      "s3:ObjectCreated:*"
    ]

    filter_prefix = "raw/b3/"
    filter_suffix = ".zip"
  }

  lambda_function {
    lambda_function_arn = var.cvm_lambda_function_arn

    events = [
      "s3:ObjectCreated:*"
    ]

    filter_prefix = "raw/cvm/"
    filter_suffix = ".zip"
  }

  lambda_function {
    lambda_function_arn = var.b3_instruments_lambda_function_arn

    events = [
      "s3:ObjectCreated:*"
    ]

    filter_prefix = "raw/b3-instruments/"
    filter_suffix = ".zip"
  }

  lambda_function {
    lambda_function_arn = var.gold_readiness_lambda_function_arn

    events = [
      "s3:ObjectCreated:*"
    ]

    filter_prefix = "control/gold-readiness/"
    filter_suffix = "_SUCCESS.json"
  }

  depends_on = [
    aws_lambda_permission.allow_s3,
    aws_lambda_permission.allow_s3_cvm,
    aws_lambda_permission.allow_s3_b3_instruments,
    aws_lambda_permission.allow_s3_gold_readiness,
  ]
}