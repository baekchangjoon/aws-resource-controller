output "mx_inbound_fqdn" {
  value = aws_route53_record.mx_inbound.fqdn
}

output "dkim_fqdns" {
  value = [for r in aws_route53_record.dkim : r.fqdn]
}
