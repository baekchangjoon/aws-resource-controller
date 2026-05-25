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

# api_endpoint, cloudfront_domain 등은 해당 모듈 구현 후 추가
