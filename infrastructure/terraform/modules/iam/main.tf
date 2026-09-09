resource "aws_iam_group" "platform_admins" {
  name = var.admin_group_name
}

resource "aws_iam_group_policy_attachment" "administrator_access" {
  group      = aws_iam_group.platform_admins.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

resource "aws_iam_user_group_membership" "platform_admin" {
  user = var.admin_user_name

  groups = [
    aws_iam_group.platform_admins.name
  ]
}