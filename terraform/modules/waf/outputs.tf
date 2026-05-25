output "web_acl_arn" {
  description = "ARN to wire into the CloudFront distribution's web_acl_id"
  value       = aws_wafv2_web_acl.web.arn
}

output "web_acl_id" {
  value = aws_wafv2_web_acl.web.id
}
