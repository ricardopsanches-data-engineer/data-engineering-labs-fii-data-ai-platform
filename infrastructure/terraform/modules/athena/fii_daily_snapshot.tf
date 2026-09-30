resource "aws_athena_named_query" "fii_daily_snapshot_sample" {
  name = "fii_daily_snapshot_sample"

  description = (
    "Sample query for the Gold Analytics FII Daily Snapshot."
  )

  database  = var.database_name
  workgroup = aws_athena_workgroup.analytics.name

  query = <<-SQL
    SELECT
        trade_date,
        ticker,
        denominacao_social,
        close_price,
        intraday_variation,
        intraday_variation_pct,
        price_range,
        price_range_pct,
        ticker_resolution_status,
        market_evidence_confidence
    FROM fii_daily_snapshot
    WHERE year = 2026
      AND month = 8
      AND day = 28
    ORDER BY ticker
    LIMIT 20;
  SQL
}