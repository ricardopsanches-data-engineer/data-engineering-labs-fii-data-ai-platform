output "schedule_name" {
  description = "Name of the EventBridge Scheduler schedule."
  value       = aws_scheduler_schedule.daily_ingestion.name
}

output "schedule_arn" {
  description = "ARN of the EventBridge Scheduler schedule."
  value       = aws_scheduler_schedule.daily_ingestion.arn
}

output "scheduler_role_arn" {
  description = "ARN of the IAM role assumed by EventBridge Scheduler."
  value       = aws_iam_role.scheduler.arn
}

output "schedule_expression" {
  description = "Schedule expression used by EventBridge Scheduler."
  value       = aws_scheduler_schedule.daily_ingestion.schedule_expression
}

output "schedule_timezone" {
  description = "Timezone used by EventBridge Scheduler."
  value       = aws_scheduler_schedule.daily_ingestion.schedule_expression_timezone
}