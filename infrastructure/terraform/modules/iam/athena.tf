resource "aws_iam_policy" "athena_admin" {
  name        = "fii-platform-athena-admin"
  description = "Permissions required to manage and use Amazon Athena for the FII Data & AI Platform."

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "AthenaWorkgroupManagement"
        Effect = "Allow"

        Action = [
          "athena:CreateWorkGroup",
          "athena:GetWorkGroup",
          "athena:UpdateWorkGroup",
          "athena:DeleteWorkGroup",
          "athena:ListWorkGroups",
          "athena:TagResource",
          "athena:UntagResource",
          "athena:ListTagsForResource"
        ]

        Resource = "*"
      },
      {
        Sid    = "AthenaQueryExecution"
        Effect = "Allow"

        Action = [
          "athena:StartQueryExecution",
          "athena:StopQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:GetQueryResultsStream",
          "athena:ListQueryExecutions",
          "athena:BatchGetQueryExecution",
          "athena:GetDatabase",
          "athena:GetTableMetadata",
          "athena:ListDatabases",
          "athena:ListTableMetadata"
        ]

        Resource = "*"
      },
      {
        Sid    = "AthenaNamedQueries"
        Effect = "Allow"

        Action = [
          "athena:CreateNamedQuery",
          "athena:GetNamedQuery",
          "athena:DeleteNamedQuery",
          "athena:ListNamedQueries",
          "athena:BatchGetNamedQuery"
        ]

        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_group_policy_attachment" "athena_admin" {
  group      = aws_iam_group.platform_admins.name
  policy_arn = aws_iam_policy.athena_admin.arn
}