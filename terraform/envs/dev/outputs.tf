output "account_id" {
  value = data.aws_caller_identity.current.account_id
}

output "addresses_table_name" {
  value = module.ddb.addresses_table_name
}

output "messages_table_name" {
  value = module.ddb.messages_table_name
}

# api_endpoint, cloudfront_domain 등은 해당 모듈 구현 후 추가
