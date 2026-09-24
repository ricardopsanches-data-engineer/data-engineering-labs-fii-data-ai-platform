resource "aws_iam_policy" "gold_operational_observability_admin" {
  name = "fii-platform-gold-operational-observability-admin"

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "GoldMetricFilterManagement"
        Effect = "Allow"

        Action = [
          "logs:PutMetricFilter",
          "logs:DeleteMetricFilter"
        ]

        Resource = [
          "arn:aws:logs:sa-east-1:625685670804:log-group:/aws/lambda/fii-data-ai-platform-dev-fii-master-gold"
        ]
      },
      {
        Sid    = "GoldMetricFilterRead"
        Effect = "Allow"

        Action = [
          "logs:DescribeMetricFilters"
        ]

        Resource = "*"
      },
      {
        Sid    = "GoldCloudWatchAlarmManagement"
        Effect = "Allow"

        Action = [
          "cloudwatch:PutMetricAlarm",
          "cloudwatch:DeleteAlarms",
          "cloudwatch:ListTagsForResource",
          "cloudwatch:TagResource",
          "cloudwatch:UntagResource"
        ]

        Resource = [
          "arn:aws:cloudwatch:sa-east-1:625685670804:alarm:fii-data-ai-platform-dev-gold-operational-errors"
        ]
      },
      {
        Sid    = "GoldCloudWatchAlarmRead"
        Effect = "Allow"

        Action = [
          "cloudwatch:DescribeAlarms"
        ]

        Resource = "*"
      },
      {
        Sid    = "GoldSnsTopicManagement"
        Effect = "Allow"

        Action = [
          "sns:CreateTopic",
          "sns:DeleteTopic",
          "sns:GetTopicAttributes",
          "sns:SetTopicAttributes",
          "sns:ListSubscriptionsByTopic",
          "sns:Subscribe",
          "sns:TagResource",
          "sns:UntagResource",
          "sns:Publish"
        ]

        Resource = [
          "arn:aws:sns:sa-east-1:625685670804:fii-data-ai-platform-dev-gold-operational-alerts"
        ]
      },
      {
        Sid    = "GoldSnsSubscriptionManagement"
        Effect = "Allow"

        Action = [
          "sns:GetSubscriptionAttributes",
          "sns:SetSubscriptionAttributes",
          "sns:Unsubscribe"
        ]

        Resource = "*"
      },
      {
        Sid    = "GoldSnsRead"
        Effect = "Allow"

        Action = [
          "sns:ListTopics",
          "sns:ListSubscriptions"
        ]

        Resource = "*"
      }
    ]
  })

  tags = {
    Project     = "fii-data-ai-platform"
    Environment = "dev"
    Component   = "GoldOperationalObservability"
    ManagedBy   = "Terraform"
  }
}

resource "aws_iam_group_policy_attachment" "gold_operational_observability_admin" {
  group      = aws_iam_group.platform_admins.name
  policy_arn = aws_iam_policy.gold_operational_observability_admin.arn
}