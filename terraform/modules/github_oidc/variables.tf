variable "name_prefix" {
  type = string
}

variable "github_repo" {
  description = "OWNER/REPO that should be allowed to assume the role"
  type        = string
}

variable "allow_branches" {
  description = "Git refs allowed to deploy (main, tags, etc.)"
  type        = list(string)
  default     = ["refs/heads/main"]
}

variable "allow_pull_requests" {
  description = "Whether to allow PR jobs to assume (read-only CI workflows can use it)"
  type        = bool
  default     = true
}
