# Inbound mail MX
resource "aws_route53_record" "mx_inbound" {
  zone_id = var.hosted_zone_id
  name    = var.domain_name
  type    = "MX"
  ttl     = 300
  records = ["10 inbound-smtp.${var.region}.amazonaws.com"]
}

# DKIM CNAMEs — SES Easy DKIM always issues exactly 3 tokens
resource "aws_route53_record" "dkim" {
  count = 3

  zone_id = var.hosted_zone_id
  name    = "${var.dkim_tokens[count.index]}._domainkey.${var.domain_name}"
  type    = "CNAME"
  ttl     = 1800
  records = ["${var.dkim_tokens[count.index]}.dkim.amazonses.com"]
}

# MAIL FROM domain — MX for bounce + SPF TXT
resource "aws_route53_record" "mail_from_mx" {
  zone_id = var.hosted_zone_id
  name    = var.mail_from_domain
  type    = "MX"
  ttl     = 300
  records = ["10 feedback-smtp.${var.region}.amazonses.com"]
}

resource "aws_route53_record" "mail_from_spf" {
  zone_id = var.hosted_zone_id
  name    = var.mail_from_domain
  type    = "TXT"
  ttl     = 300
  records = ["v=spf1 include:amazonses.com ~all"]
}

# DMARC
resource "aws_route53_record" "dmarc" {
  zone_id = var.hosted_zone_id
  name    = "_dmarc.${var.domain_name}"
  type    = "TXT"
  ttl     = 300
  records = [
    var.dmarc_report_email == ""
    ? "v=DMARC1;p=quarantine"
    : "v=DMARC1;p=quarantine;rua=mailto:${var.dmarc_report_email}"
  ]
}
