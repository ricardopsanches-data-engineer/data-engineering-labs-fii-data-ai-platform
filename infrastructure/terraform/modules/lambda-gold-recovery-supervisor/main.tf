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
  description = "Least-privilege permissions for the Gold recovery supervisor Lambda."

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "ListRecoveryDataLakeObjects"
        Effect = "Allow"

        Action = [
          "s3:ListBucket"
        ]

        Resource = var.data_lake_bucket_arn

        Condition = {
          StringLike = {
            "s3:prefix" = [
              "raw/b3/*",
              "raw/cvm/*",
              "raw/b3-instruments/*",
              "silver/b3/*",
              "silver/cvm/*",
              "silver/b3-instruments/*"
            ]
          }
        }
      },
      {
        Sid    = "ReadGoldObjects"
        Effect = "Allow"

        Action = [
          "s3:GetObject"
        ]

        Resource = (
          "${var.data_lake_bucket_arn}/gold/fii-master/*"
        )
      },
      {
        Sid    = "ReadGoldExecutionState"
        Effect = "Allow"

        Action = [
          "s3:GetObject"
        ]

        Resource = (
          "${var.data_lake_bucket_arn}/control/gold-execution/*"
        )
      },
      {
        Sid    = "InvokeGoldRecoveryTargets"
        Effect = "Allow"

        Action = [
          "lambda:InvokeFunction"
        ]

        Resource = concat(
          [
            var.gold_lambda_function_arn
          ],
          values(
            var.raw_to_silver_function_arns
          )
        )
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


resource "aws_lambda_function" "gold_recovery_supervisor" {
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
      FII_DATA_LAKE_BUCKET = (
        var.data_lake_bucket_name
      )

      FII_MASTER_GOLD_FUNCTION_NAME = (
        var.gold_lambda_function_name
      )

      FII_B3_RAW_TO_SILVER_FUNCTION_NAME = (
        var.raw_to_silver_function_names[
          "b3"
        ]
      )

      FII_CVM_RAW_TO_SILVER_FUNCTION_NAME = (
        var.raw_to_silver_function_names[
          "cvm"
        ]
      )

      FII_B3_INSTRUMENTS_RAW_TO_SILVER_FUNCTION_NAME = (
        var.raw_to_silver_function_names[
          "b3_instruments"
        ]
      )

      FII_GOLD_RECOVERY_LOOKBACK_DAYS = (
        tostring(
          var.lookback_days
        )
      )
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_execution,
    aws_cloudwatch_log_group.lambda,
  ]

  tags = var.tags
}