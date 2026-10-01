resource "aws_athena_named_query" "fii_features_sample" {
  name = "fii_features_sample"

  description = (
    "Sample query for the Gold ML FII Features dataset."
  )

  database  = var.database_name
  workgroup = aws_athena_workgroup.analytics.name

  query = <<-SQL
    SELECT
        feature_date,
        ticker,
        close_price,
        daily_return_pct,
        return_5d_pct,
        return_10d_pct,
        return_20d_pct,
        volatility_20d_pct,
        price_to_ma20,
        feature_ready,
        feature_version
    FROM fii_features
    WHERE year = 2026
      AND month = 8
    ORDER BY feature_date DESC, ticker
    LIMIT 20;
  SQL
}