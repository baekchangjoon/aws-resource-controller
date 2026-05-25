######################################################################
# SNS — fan-out for every alarm. The user has to confirm the email
# subscription once (AWS sends a confirmation link).
######################################################################

resource "aws_sns_topic" "alerts" {
  name = "${var.name_prefix}-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

######################################################################
# Lambda alarms
######################################################################

resource "aws_cloudwatch_metric_alarm" "ingest_errors" {
  alarm_name          = "${var.name_prefix}-ingest-errors"
  alarm_description   = "Lambda errors on ${var.ingest_lambda_function_name}"
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = var.lambda_error_threshold
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = var.ingest_lambda_function_name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "api_errors" {
  alarm_name          = "${var.name_prefix}-api-errors"
  alarm_description   = "Lambda errors on ${var.api_lambda_function_name}"
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = var.lambda_error_threshold
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = var.api_lambda_function_name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

######################################################################
# DLQ depth — any visible message means async invocations failed
######################################################################

resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "${var.name_prefix}-ingest-dlq-not-empty"
  alarm_description   = "Ingest Lambda DLQ has stuck messages (failed async invocations)"
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = var.dlq_name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

######################################################################
# API Gateway 5xx error rate
######################################################################

resource "aws_cloudwatch_metric_alarm" "api_5xx" {
  alarm_name          = "${var.name_prefix}-api-5xx"
  alarm_description   = "HTTP API ${var.api_gateway_id} returning 5xx responses"
  namespace           = "AWS/ApiGateway"
  metric_name         = "5xx"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiId = var.api_gateway_id
    Stage = var.api_gateway_stage
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

######################################################################
# AWS Budgets — guardrail on monthly account spend
######################################################################

resource "aws_budgets_budget" "monthly" {
  name              = "${var.name_prefix}-monthly"
  budget_type       = "COST"
  time_unit         = "MONTHLY"
  limit_amount      = tostring(var.monthly_budget_usd)
  limit_unit        = "USD"
  time_period_start = "2026-05-01_00:00"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 50
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.notification_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.notification_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.notification_email]
  }

  # Hard 100% ACTUAL trigger — fans out to the killswitch SNS topic which
  # deactivates the SES Receipt Rule Set to stop the largest cost-multiplier
  # (inbound SES + S3 PUT + Lambda invokes) immediately.
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.notification_email]
    subscriber_sns_topic_arns  = [aws_sns_topic.budget_breach.arn]
  }
}

######################################################################
# Ingest Lambda invocations spike — early warning for SES inbound flood
######################################################################

resource "aws_cloudwatch_metric_alarm" "ingest_invocations_spike" {
  alarm_name          = "${var.name_prefix}-ingest-invocations-spike"
  alarm_description   = "Ingest Lambda invocations exceeded the spike threshold — possible SES inbound flood"
  namespace           = "AWS/Lambda"
  metric_name         = "Invocations"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = var.ingest_invocations_spike_threshold
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = var.ingest_lambda_function_name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}

######################################################################
# AWS Cost Anomaly Detection — ML-driven catch for cost spikes the
# fixed-threshold budget would miss
######################################################################

resource "aws_ce_anomaly_monitor" "service" {
  name              = "${var.name_prefix}-anomaly-service"
  monitor_type      = "DIMENSIONAL"
  monitor_dimension = "SERVICE"
}

resource "aws_ce_anomaly_subscription" "service" {
  name             = "${var.name_prefix}-anomaly-service"
  frequency        = "IMMEDIATE"
  monitor_arn_list = [aws_ce_anomaly_monitor.service.arn]

  subscriber {
    type    = "EMAIL"
    address = var.notification_email
  }

  threshold_expression {
    dimension {
      key           = "ANOMALY_TOTAL_IMPACT_ABSOLUTE"
      values        = [tostring(var.cost_anomaly_total_impact_usd)]
      match_options = ["GREATER_THAN_OR_EQUAL"]
    }
  }
}

######################################################################
# Budget kill switch — Lambda that drops the active SES receipt rule
# set when the monthly budget breaches 100% ACTUAL.
######################################################################

resource "aws_sns_topic" "budget_breach" {
  name = "${var.name_prefix}-budget-breach"
}

data "aws_iam_policy_document" "budget_breach_topic" {
  statement {
    sid     = "AllowBudgetsServicePublish"
    effect  = "Allow"
    actions = ["sns:Publish"]

    principals {
      type        = "Service"
      identifiers = ["budgets.amazonaws.com"]
    }

    resources = [aws_sns_topic.budget_breach.arn]
  }
}

resource "aws_sns_topic_policy" "budget_breach" {
  arn    = aws_sns_topic.budget_breach.arn
  policy = data.aws_iam_policy_document.budget_breach_topic.json
}

data "aws_iam_policy_document" "killswitch_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "killswitch" {
  name               = "${var.name_prefix}-budget-killswitch"
  assume_role_policy = data.aws_iam_policy_document.killswitch_assume.json
}

data "aws_iam_policy_document" "killswitch" {
  statement {
    sid     = "Logs"
    effect  = "Allow"
    actions = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = [
      "arn:aws:logs:*:*:log-group:/aws/lambda/${var.name_prefix}-budget-killswitch*",
    ]
  }

  statement {
    sid    = "DeactivateSesRuleSet"
    effect = "Allow"
    # SES v1 SetActiveReceiptRuleSet does not support resource-level perms.
    actions   = ["ses:SetActiveReceiptRuleSet"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "killswitch" {
  name   = "${var.name_prefix}-budget-killswitch"
  role   = aws_iam_role.killswitch.id
  policy = data.aws_iam_policy_document.killswitch.json
}

resource "aws_cloudwatch_log_group" "killswitch" {
  name              = "/aws/lambda/${var.name_prefix}-budget-killswitch"
  retention_in_days = 30
}

resource "aws_lambda_function" "killswitch" {
  function_name    = "${var.name_prefix}-budget-killswitch"
  role             = aws_iam_role.killswitch.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.13"
  architectures    = ["x86_64"]
  timeout          = 10
  memory_size      = 128
  filename         = var.killswitch_lambda_zip_path
  source_code_hash = filebase64sha256(var.killswitch_lambda_zip_path)

  depends_on = [
    aws_iam_role_policy.killswitch,
    aws_cloudwatch_log_group.killswitch,
  ]
}

resource "aws_lambda_permission" "killswitch_sns" {
  statement_id  = "AllowBudgetBreachSNSInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.killswitch.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.budget_breach.arn
}

resource "aws_sns_topic_subscription" "killswitch" {
  topic_arn = aws_sns_topic.budget_breach.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.killswitch.arn
}
