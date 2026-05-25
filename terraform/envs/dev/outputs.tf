output "account_id" {
  value = data.aws_caller_identity.current.account_id
}

output "addresses_table_name" {
  value = module.ddb.addresses_table_name
}

output "messages_table_name" {
  value = module.ddb.messages_table_name
}

output "mail_bucket_name" {
  value = module.ingest_pipeline.mail_bucket_name
}

output "ingest_dlq_url" {
  value = module.ingest_pipeline.dlq_url
}

output "ingest_lambda_role_arn" {
  value = module.ingest_pipeline.ingest_lambda_role_arn
}

output "ses_rule_set_name" {
  value = module.ses.rule_set_name
}

output "ses_dkim_tokens" {
  value = module.ses.dkim_tokens
}

output "web_fqdn" {
  value = local.web_fqdn
}

output "api_endpoint" {
  value = module.api.api_endpoint
}

output "api_lambda_function_name" {
  value = module.api.api_lambda_function_name
}

output "web_bucket_name" {
  value = module.frontend.web_bucket_name
}

output "cloudfront_distribution_id" {
  value = module.frontend.cloudfront_distribution_id
}

output "cloudfront_domain_name" {
  value = module.frontend.cloudfront_domain_name
}

output "web_url" {
  value = module.frontend.web_url
}

output "github_deploy_role_arn" {
  value = module.github_oidc.deploy_role_arn
}
