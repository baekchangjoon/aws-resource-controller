data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Existing hosted zone (preserved — see docs/TEARDOWN.md §A)
data "aws_route53_zone" "primary" {
  name         = "${var.domain_name}."
  private_zone = false
}

locals {
  account_id     = data.aws_caller_identity.current.account_id
  region         = data.aws_region.current.name
  name_prefix    = "tempses-${var.environment}"
  web_fqdn       = "${var.web_subdomain}.${var.domain_name}"
  mail_from_fqdn = "${var.mail_from_subdomain}.${var.domain_name}"
}

module "ddb" {
  source = "../../modules/ddb"

  name_prefix         = local.name_prefix
  message_ttl_seconds = var.message_ttl_seconds
}

module "ingest_pipeline" {
  source = "../../modules/ingest_pipeline"

  name_prefix          = local.name_prefix
  account_id           = local.account_id
  region               = local.region
  addresses_table_arn  = module.ddb.addresses_table_arn
  addresses_table_name = module.ddb.addresses_table_name
  messages_table_arn   = module.ddb.messages_table_arn
  messages_table_name  = module.ddb.messages_table_name
  lambda_zip_path      = "${path.root}/../../../lambda/ingest/dist/handler.zip"
  message_ttl_seconds  = var.message_ttl_seconds
}

module "ses" {
  source = "../../modules/ses"

  name_prefix      = local.name_prefix
  domain_name      = var.domain_name
  mail_from_domain = local.mail_from_fqdn
  # personal_email is kept outside Terraform to avoid email re-verification.
  # See docs/DECISIONS.md D4.
  personal_email       = ""
  mail_bucket_name     = module.ingest_pipeline.mail_bucket_name
  s3_object_key_prefix = "emails/"
  make_rule_set_active = true
}

module "route53_records" {
  source = "../../modules/route53_records"

  hosted_zone_id     = data.aws_route53_zone.primary.zone_id
  domain_name        = var.domain_name
  mail_from_domain   = local.mail_from_fqdn
  region             = local.region
  dkim_tokens        = module.ses.dkim_tokens
  dmarc_report_email = "changjoon.baek@gmail.com"
}

module "api" {
  source = "../../modules/api"

  name_prefix          = local.name_prefix
  account_id           = local.account_id
  region               = local.region
  domain               = var.domain_name
  lambda_zip_path      = "${path.root}/../../../lambda/api/dist/handler.zip"
  addresses_table_arn  = module.ddb.addresses_table_arn
  addresses_table_name = module.ddb.addresses_table_name
  messages_table_arn   = module.ddb.messages_table_arn
  messages_table_name  = module.ddb.messages_table_name
  mail_bucket_arn      = module.ingest_pipeline.mail_bucket_arn
  mail_bucket_name     = module.ingest_pipeline.mail_bucket_name
  address_ttl_seconds  = var.message_ttl_seconds
  cors_origins = [
    "http://localhost:5173",
    "https://${local.web_fqdn}",
  ]
}

module "github_oidc" {
  source = "../../modules/github_oidc"

  name_prefix = local.name_prefix
  github_repo = "baekchangjoon/aws-resource-controller"
}

module "observability" {
  source = "../../modules/observability"

  name_prefix                 = local.name_prefix
  notification_email          = "changjoon.baek@gmail.com"
  ingest_lambda_function_name = module.ingest_pipeline.ingest_lambda_function_name
  api_lambda_function_name    = module.api.api_lambda_function_name
  dlq_name                    = module.ingest_pipeline.dlq_name
  api_gateway_id              = module.api.api_id
  monthly_budget_usd          = 10
  killswitch_lambda_zip_path  = "${path.root}/../../../lambda/budget_killswitch/dist/handler.zip"
}

module "waf" {
  source = "../../modules/waf"
  providers = {
    aws.us_east_1 = aws.us_east_1
  }

  name_prefix = local.name_prefix
}

module "frontend" {
  source = "../../modules/frontend"
  providers = {
    aws.us_east_1 = aws.us_east_1
  }

  name_prefix    = local.name_prefix
  account_id     = local.account_id
  domain_name    = var.domain_name
  web_fqdn       = local.web_fqdn
  hosted_zone_id = data.aws_route53_zone.primary.zone_id
  web_acl_arn    = module.waf.web_acl_arn
}
