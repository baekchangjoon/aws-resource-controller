######################################################################
# CloudFront-scoped WAFv2 web ACL.
#
# Three rules, evaluated in priority order:
#   1. AWS-managed CommonRuleSet   — OWASP core (SQLi, XSS, path traversal, ...).
#   2. AWS-managed KnownBadInputs  — generic malicious inputs / exploits.
#   3. IP-based rate limit         — DDoS / scraper cap per source IP.
#
# CloudFront-scope ACLs MUST live in us-east-1 regardless of where the
# distribution serves traffic from.
######################################################################

resource "aws_wafv2_web_acl" "web" {
  provider = aws.us_east_1

  name        = "${var.name_prefix}-web"
  description = "WAFv2 web ACL for the TempSES CloudFront distribution"
  scope       = "CLOUDFRONT"

  default_action {
    allow {}
  }

  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesCommonRuleSet"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.name_prefix}-common-rules"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.name_prefix}-bad-inputs"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "IPRateLimit"
    priority = 3

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = var.rate_limit
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.name_prefix}-ip-rate-limit"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.name_prefix}-web-acl"
    sampled_requests_enabled   = true
  }
}
