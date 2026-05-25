variable "region" {
  description = "Primary AWS region"
  type        = string
  default     = "ap-northeast-2"
}

variable "aws_profile" {
  description = "AWS named profile"
  type        = string
  default     = "default"
}

variable "environment" {
  description = "Environment name (dev, prod)"
  type        = string
  default     = "dev"
}

variable "domain_name" {
  description = "Root domain managed by Route53"
  type        = string
  default     = "dev-temp-mail.com"
}

variable "web_subdomain" {
  description = "Subdomain for the web frontend"
  type        = string
  default     = "app-dev"
}

variable "mail_from_subdomain" {
  description = "Subdomain used as SES MAIL FROM"
  type        = string
  default     = "bounce"
}

variable "message_ttl_seconds" {
  description = "Default TTL for messages and addresses (seconds)"
  type        = number
  default     = 7200 # 2 hours
}
