resource "aws_cloudwatch_log_metric_filter" "gold_operational_errors" {
  name = "gold-operational-errors"

  log_group_name = var.log_group_name

  pattern = "{ $.pipeline = \"gold-recovery\" && $.status = \"ERROR\" }"

  metric_transformation {
    name      = var.operational_error_metric_name
    namespace = var.metric_namespace
    value     = "1"

    default_value = 0
  }
}

resource "aws_cloudwatch_metric_alarm" "gold_operational_errors" {
  alarm_name        = var.alarm_name
  alarm_description = var.alarm_description

  namespace   = var.metric_namespace
  metric_name = var.operational_error_metric_name

  statistic = "Sum"

  period             = var.alarm_period_seconds
  evaluation_periods = var.alarm_evaluation_periods

  threshold = var.alarm_threshold

  comparison_operator = "GreaterThanOrEqualToThreshold"

  treat_missing_data = "notBreaching"

  tags = var.tags

  depends_on = [
    aws_cloudwatch_log_metric_filter.gold_operational_errors
  ]
}