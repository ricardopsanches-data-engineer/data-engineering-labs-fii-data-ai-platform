output "metric_filter_name" {
  description = "Name of the CloudWatch Logs metric filter for Gold operational errors."
  value       = aws_cloudwatch_log_metric_filter.gold_operational_errors.name
}

output "metric_namespace" {
  description = "CloudWatch namespace used for Gold operational metrics."
  value       = var.metric_namespace
}

output "operational_error_metric_name" {
  description = "CloudWatch metric name generated from Gold operational ERROR events."
  value       = var.operational_error_metric_name
}

output "alarm_name" {
  description = "Name of the CloudWatch alarm for Gold operational errors."
  value       = aws_cloudwatch_metric_alarm.gold_operational_errors.alarm_name
}

output "alarm_arn" {
  description = "ARN of the CloudWatch alarm for Gold operational errors."
  value       = aws_cloudwatch_metric_alarm.gold_operational_errors.arn
}