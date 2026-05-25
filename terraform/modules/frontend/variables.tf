variable "name_prefix" {
  type = string
}

variable "account_id" {
  type = string
}

variable "domain_name" {
  description = "Root domain (e.g. dev-temp-mail.com)"
  type        = string
}

variable "web_fqdn" {
  description = "FQDN where the SPA is served (e.g. app-dev.dev-temp-mail.com)"
  type        = string
}

variable "hosted_zone_id" {
  type = string
}

variable "price_class" {
  description = "CloudFront price class — PriceClass_100 covers NA + EU only (cheapest)"
  type        = string
  default     = "PriceClass_100"
}

variable "web_acl_arn" {
  description = "ARN of a CLOUDFRONT-scoped WAFv2 web ACL to attach. Leave null to disable WAF."
  type        = string
  default     = null
}
