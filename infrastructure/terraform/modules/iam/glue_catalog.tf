resource "aws_iam_policy" "glue_catalog_admin" {
  name        = "fii-platform-glue-catalog-admin"
  description = "Permissions required to manage the AWS Glue Data Catalog for the FII Data & AI Platform."

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "GlueCatalogManagement"
        Effect = "Allow"

        Action = [
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:CreateDatabase",
          "glue:UpdateDatabase",
          "glue:DeleteDatabase",

          "glue:GetTable",
          "glue:GetTables",
          "glue:CreateTable",
          "glue:UpdateTable",
          "glue:DeleteTable",

          "glue:GetPartition",
          "glue:GetPartitions",
          "glue:CreatePartition",
          "glue:BatchCreatePartition",
          "glue:UpdatePartition",
          "glue:DeletePartition",
          "glue:BatchDeletePartition",

          "glue:TagResource",
          "glue:UntagResource",
          "glue:GetTags"
        ]

        Resource = [
          "arn:aws:glue:sa-east-1:625685670804:catalog",
          "arn:aws:glue:sa-east-1:625685670804:database/*",
          "arn:aws:glue:sa-east-1:625685670804:table/*/*"
        ]
      }
    ]
  })
}

resource "aws_iam_group_policy_attachment" "glue_catalog_admin" {
  group      = aws_iam_group.platform_admins.name
  policy_arn = aws_iam_policy.glue_catalog_admin.arn
}