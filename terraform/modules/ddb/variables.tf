variable "name_prefix" {
  description = "Prefix used for table names"
  type        = string
}

variable "message_ttl_seconds" {
  description = "Default TTL in seconds (informational — actual TTL is set per-item by Lambdas)"
  type        = number
  default     = 7200
}
