resource "aws_athena_named_query" "fii_price_history_sample" {
  name = "fii_price_history_sample"

  description = (
    "Sample query for the Gold Analytics FII Price History."
  )

  database  = var.database_name
  workgroup = aws_athena_workgroup.analytics.name

  query = <<-SQL
    SELECT
        trade_date,
        ticker,
        close_price,
        close_price_raw,
        close_price_adjusted,
        daily_return_pct,
        return_5d_pct,
        return_20d_pct,
        volatility_20d_pct,
        confirmed_action_on_date,
        price_history_version
    FROM fii_price_history
    WHERE year = 2026
      AND month = 8
    ORDER BY trade_date DESC, ticker
    LIMIT 20;
  SQL
}