output "admin_group_name" {
  description = "IAM administrators group managed by Terraform."
  value       = aws_iam_group.platform_admins.name
}