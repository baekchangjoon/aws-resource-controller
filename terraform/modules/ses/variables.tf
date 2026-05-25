variable "name_prefix" {
  description = "Resource name prefix"
  type        = string
}

variable "domain_name" {
  description = "Email-receiving domain (e.g. dev-temp-mail.com)"
  type        = string
}

variable "mail_from_domain" {
  description = "Subdomain used as SES MAIL FROM (e.g. bounce.dev-temp-mail.com)"
  type        = string
}

variable "personal_email" {
  description = "Optional personal email identity (for outbound testing). Set to empty string to skip."
  type        = string
  default     = ""
}

variable "mail_bucket_name" {
  description = "S3 bucket name where SES receipt rule writes raw emails"
  type        = string
}

variable "s3_object_key_prefix" {
  description = "Object key prefix within the bucket for SES action"
  type        = string
  default     = "emails/"
}

variable "make_rule_set_active" {
  description = "Whether to set this receipt rule set as the active one (only one can be active per region)"
  type        = bool
  default     = true
}
