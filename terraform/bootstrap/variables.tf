variable "region" {
  description = "AWS region for state resources"
  type        = string
  default     = "ap-northeast-2"
}

variable "aws_profile" {
  description = "AWS named profile to use"
  type        = string
  default     = "default"
}

variable "state_bucket_name" {
  description = "Name of the S3 bucket for Terraform state"
  type        = string
  default     = "tempses-tfstate-322242916220"
}

variable "lock_table_name" {
  description = "Name of the DynamoDB table for Terraform state lock"
  type        = string
  default     = "tempses-tflock"
}
