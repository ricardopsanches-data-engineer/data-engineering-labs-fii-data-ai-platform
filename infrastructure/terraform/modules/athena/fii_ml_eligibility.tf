resource "aws_athena_named_query" "fii_ml_eligibility_sample" {
  name = "fii_ml_eligibility_sample"

  description = (
    "Sample query for the Gold ML FII ML Eligibility dataset."
  )

  database  = var.database_name
  workgroup = aws_athena_workgroup.analytics.name

  query = <<-SQL
    SELECT
        ticker,
        feature_date,
        target_date,
        feature_window_clean,
        target_horizon_clean,
        ml_eligible,
        ml_ineligibility_reason,
        ml_eligibility_version,
        source_feature_version,
        source_price_quality_version
    FROM fii_ml_eligibility
    ORDER BY feature_date DESC, ticker
    LIMIT 20;
  SQL
}