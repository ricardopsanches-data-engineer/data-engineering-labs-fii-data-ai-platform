module "budget" {
  source = "../../modules/budget"

  budget_name        = "fii-data-ai-platform-dev-monthly"
  limit_amount       = var.budget_limit_usd
  notification_email = var.budget_notification_email
}

module "iam" {
  source = "../../modules/iam"

  admin_group_name = "fii-platform-admins"
  admin_user_name  = "fii-platform-admin"
}