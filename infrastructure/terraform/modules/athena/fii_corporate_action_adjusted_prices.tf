resource "aws_athena_named_query" "fii_corporate_action_adjusted_prices_sample" {
  name = "fii_corporate_action_adjusted_prices_sample"

  description = (
    "Sample query for the Gold Analytics Corporate Action Adjusted Prices."
  )

  database  = var.database_name
  workgroup = aws_athena_workgroup.analytics.name

  query = <<-SQL
    SELECT
        trade_date,
        ticker,
        close_price_raw,
        close_price_adjusted,
        structural_adjustment_factor,
        daily_return_raw,
        daily_return_adjusted_price,
        daily_return_economic,
        confirmed_action_on_date,
        confirmed_event_type,
        adjusted_prices_version
    FROM fii_corporate_action_adjusted_prices
    WHERE year = 2026
    ORDER BY trade_date DESC, ticker
    LIMIT 20;
  SQL
}