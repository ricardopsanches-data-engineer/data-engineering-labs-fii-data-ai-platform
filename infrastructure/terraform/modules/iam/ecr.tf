resource "aws_iam_policy" "ecr_admin" {
  name        = "fii-platform-ecr-admin"
  description = "Permissions required to manage and publish container images for the FII Data & AI Platform."

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "EcrAuthorization"
        Effect = "Allow"

        Action = [
          "ecr:GetAuthorizationToken"
        ]

        Resource = "*"
      },
      {
        Sid    = "EcrSilverRepositoryManagement"
        Effect = "Allow"

        Action = [
          "ecr:CreateRepository",
          "ecr:DeleteRepository",
          "ecr:DescribeRepositories",
          "ecr:GetRepositoryPolicy",
          "ecr:SetRepositoryPolicy",
          "ecr:DeleteRepositoryPolicy",
          "ecr:PutImageScanningConfiguration",
          "ecr:PutImageTagMutability",
          "ecr:ListTagsForResource",
          "ecr:TagResource",
          "ecr:UntagResource"
        ]

        Resource = [
          "arn:aws:ecr:sa-east-1:625685670804:repository/fii-data-ai-platform-dev-*-silver"
        ]
      },
      {
        Sid    = "EcrSilverImageManagement"
        Effect = "Allow"

        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage",
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer",
          "ecr:DescribeImages",
          "ecr:ListImages"
        ]

        Resource = [
          "arn:aws:ecr:sa-east-1:625685670804:repository/fii-data-ai-platform-dev-*-silver"
        ]
      }
    ]
  })
}

resource "aws_iam_group_policy_attachment" "ecr_admin" {
  group      = aws_iam_group.platform_admins.name
  policy_arn = aws_iam_policy.ecr_admin.arn
}