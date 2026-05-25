variable "name_prefix" {
  type = string
}

variable "rate_limit" {
  description = "Requests per 5-minute window per source IP before WAF blocks (AWS minimum is 100)"
  type        = number
  default     = 2000
}
