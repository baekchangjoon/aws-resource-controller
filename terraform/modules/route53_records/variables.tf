variable "hosted_zone_id" {
  description = "Route53 hosted zone ID (existing)"
  type        = string
}

variable "domain_name" {
  description = "Primary domain (e.g. dev-temp-mail.com)"
  type        = string
}

variable "mail_from_domain" {
  description = "MAIL FROM subdomain (e.g. bounce.dev-temp-mail.com)"
  type        = string
}

variable "region" {
  description = "AWS region for SES inbound endpoint"
  type        = string
}

variable "dkim_tokens" {
  description = "DKIM tokens from SES domain identity"
  type        = list(string)
}

variable "dmarc_report_email" {
  description = "Email to receive DMARC aggregate reports"
  type        = string
  default     = ""
}
