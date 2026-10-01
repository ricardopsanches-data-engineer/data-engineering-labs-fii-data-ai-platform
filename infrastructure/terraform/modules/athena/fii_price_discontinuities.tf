resource "aws_athena_named_query" "fii_price_discontinuities_sample" {
  name = "fii_price_discontinuities_sample"

  description = (
    "Sample query for the Gold Analytics FII Price Discontinuities."
  )

  database  = var.database_name
  workgroup = aws_athena_workgroup.analytics.name

  query = <<-SQL
    SELECT
        event_date,
        ticker,
        price_before,
        price_after,
        daily_return_pct,
        classification,
        confidence,
        review_status,
        event_type,
        is_confirmed_corporate_action,
        newly_visible_in_v5_band,
        discontinuity_version
    FROM fii_price_discontinuities
    ORDER BY event_date DESC, ticker
    LIMIT 20;
  SQL
}