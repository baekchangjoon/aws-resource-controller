######################################################################
# Domain identity (SES v2)
######################################################################

resource "aws_sesv2_email_identity" "domain" {
  email_identity = var.domain_name

  dkim_signing_attributes {
    next_signing_key_length = "RSA_2048_BIT"
  }
}

resource "aws_sesv2_email_identity_mail_from_attributes" "domain" {
  email_identity         = aws_sesv2_email_identity.domain.email_identity
  behavior_on_mx_failure = "USE_DEFAULT_VALUE"
  mail_from_domain       = var.mail_from_domain
}

######################################################################
# Personal email identity (optional, for outbound testing)
######################################################################

resource "aws_sesv2_email_identity" "personal" {
  count          = var.personal_email == "" ? 0 : 1
  email_identity = var.personal_email
}

######################################################################
# Receipt rule set — receives mail for the domain and stores raw mail in S3
######################################################################

resource "aws_ses_receipt_rule_set" "main" {
  rule_set_name = "${var.name_prefix}-rules"
}

resource "aws_ses_active_receipt_rule_set" "main" {
  count         = var.make_rule_set_active ? 1 : 0
  rule_set_name = aws_ses_receipt_rule_set.main.rule_set_name
}

resource "aws_ses_receipt_rule" "catch_all" {
  name          = "${var.name_prefix}-catch-all"
  rule_set_name = aws_ses_receipt_rule_set.main.rule_set_name
  recipients    = [var.domain_name]
  enabled       = true
  scan_enabled  = true
  tls_policy    = "Optional"

  s3_action {
    position          = 1
    bucket_name       = var.mail_bucket_name
    object_key_prefix = var.s3_object_key_prefix
  }
}
