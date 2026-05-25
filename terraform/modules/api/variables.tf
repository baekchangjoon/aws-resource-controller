variable "name_prefix" {
  description = "Resource name prefix (e.g. tempses-dev)"
  type        = string
}

variable "account_id" {
  type = string
}

variable "region" {
  type = string
}

variable "domain" {
  description = "Email-receiving domain (e.g. dev-temp-mail.com)"
  type        = string
}

variable "lambda_zip_path" {
  description = "Path to the API Lambda deploy zip"
  type        = string
}

variable "addresses_table_arn" {
  type = string
}

variable "addresses_table_name" {
  type = string
}

variable "messages_table_arn" {
  type = string
}

variable "messages_table_name" {
  type = string
}

variable "mail_bucket_arn" {
  type = string
}

variable "mail_bucket_name" {
  type = string
}

variable "address_ttl_seconds" {
  type    = number
  default = 7200
}

variable "presign_expires_seconds" {
  type    = number
  default = 300
}

variable "cors_origins" {
  description = "Allowed origins for the HTTP API CORS configuration"
  type        = list(string)
  default     = ["http://localhost:5173"]
}

variable "log_retention_days" {
  type    = number
  default = 7
}
