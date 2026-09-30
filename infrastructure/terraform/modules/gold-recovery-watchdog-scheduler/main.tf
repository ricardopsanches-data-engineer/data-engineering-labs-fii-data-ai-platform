resource "aws_iam_role" "scheduler" {
  name = "${var.schedule_name_prefix}-scheduler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect = "Allow"

        Principal = {
          Service = "scheduler.amazonaws.com"
        }

        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = var.tags
}


resource "aws_iam_role_policy" "invoke_supervisor" {
  name = "${var.schedule_name_prefix}-invoke-supervisor"
  role = aws_iam_role.scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "InvokeGoldRecoverySupervisor"
        Effect = "Allow"

        Action = [
          "lambda:InvokeFunction"
        ]

        Resource = var.supervisor_lambda_arn
      }
    ]
  })
}


resource "aws_scheduler_schedule" "watchdog" {
  for_each = var.checks

  name = (
    "${var.schedule_name_prefix}-${each.key}"
  )

  description = (
    each.value.verification_only
    ? "Gold recovery watchdog final verification at ${each.value.hour}:00."
    : "Gold recovery watchdog attempt ${each.value.attempt}/${each.value.max_attempts} at ${each.value.hour}:00."
  )

  schedule_expression = (
    "cron(0 ${each.value.hour} ? * MON-FRI *)"
  )

  schedule_expression_timezone = (
    var.schedule_timezone
  )

  state = (
    var.enabled
    ? "ENABLED"
    : "DISABLED"
  )

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = var.supervisor_lambda_arn
    role_arn = aws_iam_role.scheduler.arn

    input = jsonencode({
      trigger           = "watchdog"
      attempt           = each.value.attempt
      max_attempts      = each.value.max_attempts
      final_attempt     = each.value.final_attempt
      verification_only = each.value.verification_only
      check_hour        = each.value.hour
      lookback_days     = var.lookback_days
    })

    retry_policy {
      maximum_event_age_in_seconds = (
        var.maximum_event_age_seconds
      )

      maximum_retry_attempts = (
        var.maximum_retry_attempts
      )
    }
  }

  depends_on = [
    aws_iam_role_policy.invoke_supervisor
  ]
}