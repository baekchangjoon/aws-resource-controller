output "domain_identity_arn" {
  value = aws_sesv2_email_identity.domain.arn
}

output "dkim_tokens" {
  description = "DKIM tokens to publish as CNAMEs in Route53"
  value       = aws_sesv2_email_identity.domain.dkim_signing_attributes[0].tokens
}

output "mail_from_domain" {
  value = var.mail_from_domain
}

output "domain_name" {
  value = var.domain_name
}

output "rule_set_name" {
  value = aws_ses_receipt_rule_set.main.rule_set_name
}
