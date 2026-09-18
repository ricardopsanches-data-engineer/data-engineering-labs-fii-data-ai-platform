resource "aws_iam_policy" "lambda_gold_readiness_admin" {
  name        = "fii-platform-lambda-gold-readiness-admin"
  description = "Permissions required to manage the Gold readiness coordinator Lambda."

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "GoldReadinessExecutionRoleRead"
        Effect = "Allow"

        Action = [
          "iam:GetRole",
          "iam:ListAttachedRolePolicies",
          "iam:ListRolePolicies",
          "iam:ListInstanceProfilesForRole",
          "iam:ListRoleTags"
        ]

        Resource = [
          "arn:aws:iam::625685670804:role/fii-data-ai-platform-dev-gold-readiness-execution-role"
        ]
      },
      {
        Sid    = "GoldReadinessExecutionRoleManagement"
        Effect = "Allow"

        Action = [
          "iam:CreateRole",
          "iam:DeleteRole",
          "iam:UpdateAssumeRolePolicy",
          "iam:TagRole",
          "iam:UntagRole",
          "iam:AttachRolePolicy",
          "iam:DetachRolePolicy"
        ]

        Resource = [
          "arn:aws:iam::625685670804:role/fii-data-ai-platform-dev-gold-readiness-execution-role"
        ]
      },
      {
        Sid    = "GoldReadinessPassExecutionRole"
        Effect = "Allow"

        Action = [
          "iam:PassRole"
        ]

        Resource = [
          "arn:aws:iam::625685670804:role/fii-data-ai-platform-dev-gold-readiness-execution-role"
        ]

        Condition = {
          StringEquals = {
            "iam:PassedToService" = "lambda.amazonaws.com"
          }
        }
      },
      {
        Sid    = "GoldReadinessLambdaManagement"
        Effect = "Allow"

        Action = [
          "lambda:CreateFunction",
          "lambda:GetFunction",
          "lambda:GetFunctionConfiguration",
          "lambda:GetFunctionConcurrency",
          "lambda:GetFunctionCodeSigningConfig",
          "lambda:GetRuntimeManagementConfig",
          "lambda:ListVersionsByFunction",
          "lambda:UpdateFunctionCode",
          "lambda:UpdateFunctionConfiguration",
          "lambda:DeleteFunction",
          "lambda:InvokeFunction",
          "lambda:GetPolicy",
          "lambda:AddPermission",
          "lambda:RemovePermission",
          "lambda:ListTags",
          "lambda:TagResource",
          "lambda:UntagResource"
        ]

        Resource = [
          "arn:aws:lambda:sa-east-1:625685670804:function:fii-data-ai-platform-dev-gold-readiness"
        ]
      },
      {
        Sid    = "GoldReadinessLogGroupManagement"
        Effect = "Allow"

        Action = [
          "logs:CreateLogGroup",
          "logs:DeleteLogGroup",
          "logs:PutRetentionPolicy",
          "logs:DeleteRetentionPolicy",
          "logs:ListTagsForResource",
          "logs:TagResource",
          "logs:UntagResource"
        ]

        Resource = [
          "arn:aws:logs:sa-east-1:625685670804:log-group:/aws/lambda/fii-data-ai-platform-dev-gold-readiness*"
        ]
      }
    ]
  })
}

resource "aws_iam_group_policy_attachment" "lambda_gold_readiness_admin" {
  group      = aws_iam_group.platform_admins.name
  policy_arn = aws_iam_policy.lambda_gold_readiness_admin.arn
}