output "budget_name" {
  description = "Name of the created AWS Budget."
  value       = aws_budgets_budget.monthly_cost.name
}