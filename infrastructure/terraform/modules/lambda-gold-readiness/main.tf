resource "aws_iam_role" "lambda_execution" {
  name = "${var.function_name}-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect = "Allow"

        Principal = {
          Service = "lambda.amazonaws.com"
        }

        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_policy" "lambda_execution" {
  name        = "${var.function_name}-execution-policy"
  description = "Least-privilege permissions for the Gold readiness coordinator Lambda."

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "GoldReadinessControlObjects"
        Effect = "Allow"

        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]

        Resource = "${var.data_lake_bucket_arn}/control/gold-readiness/*"
      },
      {
        Sid    = "InvokeGoldLambda"
        Effect = "Allow"

        Action = [
          "lambda:InvokeFunction"
        ]

        Resource = var.gold_lambda_function_arn
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"

        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]

        Resource = "${aws_cloudwatch_log_group.lambda.arn}:*"
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "lambda_execution" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = aws_iam_policy.lambda_execution.arn
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_lambda_function" "gold_readiness" {
  function_name = var.function_name

  role    = aws_iam_role.lambda_execution.arn
  handler = var.handler
  runtime = var.runtime

  filename         = var.filename
  source_code_hash = var.source_code_hash

  timeout     = var.timeout
  memory_size = var.memory_size

  environment {
    variables = {
      FII_DATA_LAKE_BUCKET          = var.data_lake_bucket_name
      FII_MASTER_GOLD_FUNCTION_NAME = var.gold_lambda_function_name
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_execution,
    aws_cloudwatch_log_group.lambda,
  ]

  tags = var.tags
}