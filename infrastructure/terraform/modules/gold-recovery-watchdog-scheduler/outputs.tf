output "schedule_names" {
  description = "Names of the Gold recovery watchdog schedules."

  value = {
    for key, schedule
    in aws_scheduler_schedule.watchdog :
    key => schedule.name
  }
}


output "schedule_arns" {
  description = "ARNs of the Gold recovery watchdog schedules."

  value = {
    for key, schedule
    in aws_scheduler_schedule.watchdog :
    key => schedule.arn
  }
}


output "scheduler_role_arn" {
  description = "ARN of the IAM role assumed by EventBridge Scheduler."
  value       = aws_iam_role.scheduler.arn
}


output "schedule_timezone" {
  description = "Timezone used by the Gold recovery watchdog schedules."
  value       = var.schedule_timezone
}


output "checks" {
  description = "Configured Gold recovery watchdog checks."
  value       = var.checks
}