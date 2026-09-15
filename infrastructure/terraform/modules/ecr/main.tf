resource "aws_ecr_repository" "this" {
  name                 = var.repository_name
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = var.tags
}

resource "aws_ecr_repository_policy" "lambda" {
  repository = aws_ecr_repository.this.name

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "LambdaECRImageRetrievalPolicy"
        Effect = "Allow"

        Principal = {
          Service = "lambda.amazonaws.com"
        }

        Action = [
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]

        Condition = {
          ArnLike = {
            "aws:SourceArn" = var.lambda_source_arn
          }
        }
      }
    ]
  })
}