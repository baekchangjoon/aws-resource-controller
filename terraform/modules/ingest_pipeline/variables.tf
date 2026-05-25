variable "name_prefix" {
  description = "Resource name prefix (e.g. tempses-dev)"
  type        = string
}

variable "addresses_table_arn" {
  description = "ARN of the addresses DynamoDB table"
  type        = string
}

variable "messages_table_arn" {
  description = "ARN of the messages DynamoDB table"
  type        = string
}

variable "account_id" {
  description = "AWS Account ID"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "emails_expire_days" {
  description = "S3 lifecycle: days until SES raw emails expire"
  type        = number
  default     = 1
}

variable "attachments_expire_days" {
  description = "S3 lifecycle: days until attachments expire"
  type        = number
  default     = 7
}

variable "addresses_table_name" {
  description = "Name of the addresses DynamoDB table (for env var)"
  type        = string
}

variable "messages_table_name" {
  description = "Name of the messages DynamoDB table (for env var)"
  type        = string
}

variable "lambda_zip_path" {
  description = "Path to the built Lambda Ingest deploy zip"
  type        = string
}

variable "message_ttl_seconds" {
  description = "How long a stored message lives (passed to Lambda as env var)"
  type        = number
  default     = 7200
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention for the ingest Lambda"
  type        = number
  default     = 7
}
