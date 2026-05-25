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
