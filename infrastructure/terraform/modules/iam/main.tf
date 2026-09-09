resource "aws_iam_group" "platform_admins" {
  name = var.admin_group_name
}

resource "aws_iam_policy" "phase1_admin" {
  name        = "fii-platform-phase1-admin"
  description = "Permissions required to manage the FII Data & AI Platform AWS Foundation during Phase 1."

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "TerraformStateS3"
        Effect = "Allow"

        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation",
          "s3:GetBucketVersioning",
          "s3:GetEncryptionConfiguration",
          "s3:GetBucketPublicAccessBlock",
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]

        Resource = [
          "arn:aws:s3:::fii-data-ai-platform-tfstate-625685670804",
          "arn:aws:s3:::fii-data-ai-platform-tfstate-625685670804/*"
        ]
      },
      {
        Sid    = "BudgetManagement"
        Effect = "Allow"

        Action = [
          "budgets:ViewBudget",
          "budgets:ModifyBudget",
          "budgets:ListTagsForResource",
          "budgets:TagResource",
          "budgets:UntagResource"
        ]

        Resource = "*"
      },
      {
        Sid    = "IamFoundationRead"
        Effect = "Allow"

        Action = [
          "iam:GetGroup",
          "iam:ListGroupsForUser",
          "iam:ListGroups",
          "iam:ListAttachedGroupPolicies",
          "iam:ListAttachedUserPolicies",
          "iam:GetUser",
          "iam:ListPolicies",
          "iam:GetPolicy",
          "iam:GetPolicyVersion",
          "iam:ListPolicyVersions",
          "iam:ListEntitiesForPolicy",
          "iam:ListPolicyTags"
        ]

        Resource = "*"
      },
      {
        Sid    = "IamFoundationManage"
        Effect = "Allow"

        Action = [
          "iam:CreatePolicy",
          "iam:DeletePolicy",
          "iam:CreatePolicyVersion",
          "iam:DeletePolicyVersion",
          "iam:SetDefaultPolicyVersion",
          "iam:AttachGroupPolicy",
          "iam:DetachGroupPolicy",
          "iam:AddUserToGroup",
          "iam:RemoveUserFromGroup",
          "iam:TagPolicy",
          "iam:UntagPolicy"
        ]

        Resource = "*"
      },
      {
        Sid    = "IdentityVerification"
        Effect = "Allow"

        Action = [
          "sts:GetCallerIdentity"
        ]

        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_group_policy_attachment" "phase1_admin" {
  group      = aws_iam_group.platform_admins.name
  policy_arn = aws_iam_policy.phase1_admin.arn
}

resource "aws_iam_user_group_membership" "platform_admin" {
  user = var.admin_user_name

  groups = [
    aws_iam_group.platform_admins.name
  ]
}