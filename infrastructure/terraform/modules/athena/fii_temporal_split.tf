resource "aws_athena_named_query" "fii_temporal_split_sample" {
  name = "fii_temporal_split_sample"

  description = (
    "Sample query for the Gold ML FII Temporal Split dataset."
  )

  database  = var.database_name
  workgroup = aws_athena_workgroup.analytics.name

  query = <<-SQL
    SELECT
        split,
        split_name,
        feature_date,
        target_date,
        ticker,
        close_price,
        return_5d_pct,
        return_20d_pct,
        volatility_20d_pct,
        target_return_next_5d_pct,
        ml_eligible,
        split_version,
        validation_start,
        test_start,
        split_purge_semantics,
        test_holdout_policy
    FROM fii_temporal_split
    WHERE split = 'test'
    ORDER BY feature_date DESC, ticker
    LIMIT 20;
  SQL
}