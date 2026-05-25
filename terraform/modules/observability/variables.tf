variable "name_prefix" {
  type = string
}

variable "notification_email" {
  description = "Email to receive SNS alarm notifications + AWS Budgets alerts"
  type        = string
}

variable "ingest_lambda_function_name" {
  type = string
}

variable "api_lambda_function_name" {
  type = string
}

variable "dlq_name" {
  description = "Name of the ingest SQS DLQ (for the ApproximateNumberOfMessagesVisible metric)"
  type        = string
}

variable "api_gateway_id" {
  description = "HTTP API ID for the 5xx error rate alarm"
  type        = string
}

variable "api_gateway_stage" {
  description = "Stage name on the HTTP API (default is \"$default\")"
  type        = string
  default     = "$default"
}

variable "monthly_budget_usd" {
  description = "Hard ceiling for the monthly cost alarm (alerts at 50/80/100%)"
  type        = number
  default     = 10
}

variable "lambda_error_threshold" {
  description = "Number of Lambda errors per 5-minute window before alarming"
  type        = number
  default     = 1
}
