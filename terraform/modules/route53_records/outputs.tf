output "mx_inbound_fqdn" {
  value = aws_route53_record.mx_inbound.fqdn
}

output "dkim_fqdns" {
  value = aws_route53_record.dkim[*].fqdn
}
