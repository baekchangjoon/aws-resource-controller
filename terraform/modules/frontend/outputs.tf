output "web_bucket_name" {
  value = aws_s3_bucket.web.bucket
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.web.id
}

output "cloudfront_domain_name" {
  value = aws_cloudfront_distribution.web.domain_name
}

output "web_url" {
  value = "https://${var.web_fqdn}"
}

output "acm_certificate_arn" {
  value = aws_acm_certificate_validation.cf.certificate_arn
}
