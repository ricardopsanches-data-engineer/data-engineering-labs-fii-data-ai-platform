resource "aws_athena_named_query" "fii_training_dataset_sample" {
  name = "fii_training_dataset_sample"

  description = (
    "Sample query for the Gold ML FII Training Dataset."
  )

  database  = var.database_name
  workgroup = aws_athena_workgroup.analytics.name

  query = <<-SQL
    SELECT
        feature_date,
        target_date,
        ticker,
        close_price,
        return_5d_pct,
        return_20d_pct,
        volatility_20d_pct,
        price_to_ma20,
        ml_eligible,
        target_return_next_5d_pct,
        target_price_return_next_5d_pct,
        target_economic_vs_price_difference_pct,
        training_dataset_version
    FROM fii_training_dataset
    WHERE year = 2026
      AND month = 8
      AND ml_eligible = true
    ORDER BY feature_date DESC, ticker
    LIMIT 20;
  SQL
}