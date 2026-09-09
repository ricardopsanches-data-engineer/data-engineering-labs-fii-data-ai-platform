variable "admin_group_name" {
  description = "IAM group used by administrators of the FII Data & AI Platform."
  type        = string
}

variable "admin_user_name" {
  description = "Existing IAM human user added to the platform administrators group."
  type        = string
}