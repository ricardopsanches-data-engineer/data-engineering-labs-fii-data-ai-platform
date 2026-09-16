resource "aws_athena_workgroup" "analytics" {
  name        = var.workgroup_name
  description = "Athena analytics workgroup for the FII Data & AI Platform."

  state = "ENABLED"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true
    requester_pays_enabled             = false

    bytes_scanned_cutoff_per_query = var.bytes_scanned_cutoff_per_query

    result_configuration {
      output_location = "s3://${var.data_lake_bucket_name}/${var.query_results_prefix}/"

      expected_bucket_owner = data.aws_caller_identity.current.account_id

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }

  tags = var.tags
}

data "aws_caller_identity" "current" {}

resource "aws_athena_named_query" "b3_daily_sample" {
  name        = "b3_daily_sample"
  description = "Sample query for B3 Silver trades."

  database  = var.database_name
  workgroup = aws_athena_workgroup.analytics.name

  query = <<-SQL
    SELECT
        trade_date,
        ticker,
        close_price,
        trades_quantity,
        year,
        month,
        day
    FROM b3_trades
    WHERE year = 2026
      AND month = 9
      AND day = 15
    LIMIT 20;
  SQL
}