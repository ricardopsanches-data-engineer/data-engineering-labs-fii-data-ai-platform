output "database_name" {
  description = "Name of the Glue Data Catalog database."
  value       = aws_glue_catalog_database.analytics.name
}

output "b3_table_name" {
  description = "Name of the Glue Catalog table for B3 Silver trades."
  value       = aws_glue_catalog_table.b3_trades.name
}

output "b3_table_arn" {
  description = "ARN of the Glue Catalog table for B3 Silver trades."
  value       = aws_glue_catalog_table.b3_trades.arn
}