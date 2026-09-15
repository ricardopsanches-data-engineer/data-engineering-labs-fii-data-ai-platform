resource "aws_iam_role" "scheduler" {
  name = "${var.schedule_name}-role"

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

resource "aws_iam_role_policy" "invoke_lambda" {
  name = "${var.schedule_name}-invoke-lambda"
  role = aws_iam_role.scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "InvokeDailyIngestionLambda"
        Effect = "Allow"

        Action = [
          "lambda:InvokeFunction"
        ]

        Resource = var.lambda_function_arn
      }
    ]
  })
}

resource "aws_scheduler_schedule" "daily_ingestion" {
  name        = var.schedule_name
  description = var.description

  schedule_expression          = var.schedule_expression
  schedule_expression_timezone = var.schedule_timezone

  state = var.enabled ? "ENABLED" : "DISABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = var.lambda_function_arn
    role_arn = aws_iam_role.scheduler.arn

    input = jsonencode({})

    retry_policy {
      maximum_event_age_in_seconds = var.maximum_event_age_seconds
      maximum_retry_attempts       = var.maximum_retry_attempts
    }
  }

  depends_on = [
    aws_iam_role_policy.invoke_lambda,
  ]
}