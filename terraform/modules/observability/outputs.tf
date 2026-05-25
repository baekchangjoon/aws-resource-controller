output "alerts_topic_arn" {
  value = aws_sns_topic.alerts.arn
}

output "alarm_names" {
  value = [
    aws_cloudwatch_metric_alarm.ingest_errors.alarm_name,
    aws_cloudwatch_metric_alarm.api_errors.alarm_name,
    aws_cloudwatch_metric_alarm.dlq_messages.alarm_name,
    aws_cloudwatch_metric_alarm.api_5xx.alarm_name,
  ]
}

output "budget_name" {
  value = aws_budgets_budget.monthly.name
}
