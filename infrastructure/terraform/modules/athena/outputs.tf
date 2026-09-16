output "workgroup_name" {
  description = "Name of the Athena analytics workgroup."
  value       = aws_athena_workgroup.analytics.name
}

output "workgroup_arn" {
  description = "ARN of the Athena analytics workgroup."
  value       = aws_athena_workgroup.analytics.arn
}

output "query_results_location" {
  description = "S3 location used to store Athena query results."
  value       = "s3://${var.data_lake_bucket_name}/${var.query_results_prefix}/"
}

output "named_query_id" {
  description = "ID of the sample B3 Athena named query."
  value       = aws_athena_named_query.b3_daily_sample.id
}