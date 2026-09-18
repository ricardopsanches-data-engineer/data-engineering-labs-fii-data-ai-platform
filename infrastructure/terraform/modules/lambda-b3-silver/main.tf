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
  description = "Least-privilege permissions for the B3 RAW to Silver Lambda."

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "DataLakeBucketLocation"
        Effect = "Allow"

        Action = [
          "s3:GetBucketLocation"
        ]

        Resource = var.data_lake_bucket_arn
      },
      {
        Sid    = "DataLakeB3List"
        Effect = "Allow"

        Action = [
          "s3:ListBucket"
        ]

        Resource = var.data_lake_bucket_arn

        Condition = {
          StringLike = {
            "s3:prefix" = [
              "raw/b3/*",
              "silver/b3/*"
            ]
          }
        }
      },
      {
        Sid    = "ReadB3Raw"
        Effect = "Allow"

        Action = [
          "s3:GetObject"
        ]

        Resource = "${var.data_lake_bucket_arn}/raw/b3/*"
      },
      {
        Sid    = "ReadWriteB3Silver"
        Effect = "Allow"

        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]

        Resource = "${var.data_lake_bucket_arn}/silver/b3/*"
      },
      {
        Sid    = "WriteGoldReadinessMarker"
        Effect = "Allow"

        Action = [
          "s3:PutObject"
        ]

        Resource = "${var.data_lake_bucket_arn}/control/gold-readiness/*"
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

resource "aws_lambda_function" "b3_raw_to_silver" {
  function_name = var.function_name

  role         = aws_iam_role.lambda_execution.arn
  package_type = "Image"
  image_uri    = var.image_uri

  timeout     = var.timeout
  memory_size = var.memory_size

  architectures = [
    "x86_64"
  ]

  environment {
    variables = {
      FII_DATA_LAKE_BUCKET = var.data_lake_bucket_name
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_execution,
    aws_cloudwatch_log_group.lambda,
  ]

  tags = var.tags
}