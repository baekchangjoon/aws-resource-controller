data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Existing hosted zone (preserved — see docs/TEARDOWN.md §A)
data "aws_route53_zone" "primary" {
  name         = "${var.domain_name}."
  private_zone = false
}

locals {
  account_id     = data.aws_caller_identity.current.account_id
  name_prefix    = "tempses-${var.environment}"
  web_fqdn       = "${var.web_subdomain}.${var.domain_name}"
  mail_from_fqdn = "${var.mail_from_subdomain}.${var.domain_name}"
  common_tags = {
    Project     = "tempses"
    Environment = var.environment
  }
}

module "ddb" {
  source = "../../modules/ddb"

  name_prefix         = local.name_prefix
  message_ttl_seconds = var.message_ttl_seconds
}

# Subsequent modules added as they are implemented:
# module "ses"                { ... }
# module "ingest_pipeline"    { ... }
# module "api"                { ... }
# module "frontend"           { ... }
# module "route53_records"    { ... }
