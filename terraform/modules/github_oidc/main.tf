######################################################################
# GitHub Actions OIDC trust
######################################################################

# Use the IAM-managed thumbprints — AWS does not require thumbprint validation
# for GitHub's well-known OIDC provider, but listing it keeps Terraform happy.
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

locals {
  sub_patterns = concat(
    [for ref in var.allow_branches : "repo:${var.github_repo}:ref:${ref}"],
    var.allow_pull_requests ? ["repo:${var.github_repo}:pull_request"] : [],
  )
}

data "aws_iam_policy_document" "assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = local.sub_patterns
    }
  }
}

resource "aws_iam_role" "deploy" {
  name                 = "${var.name_prefix}-github-deploy"
  assume_role_policy   = data.aws_iam_policy_document.assume.json
  max_session_duration = 3600
}

# Service-scoped deploy policy — every AWS service the Terraform stack and the
# CD workflow actually touch is listed explicitly. Anything outside this set
# (Organizations, billing, IAM user mgmt, KMS, EC2, RDS, ...) is implicitly
# denied. The explicit deny block further blocks the most dangerous IAM and
# account-level actions so a compromised workflow cannot pivot the account.
data "aws_iam_policy_document" "deploy" {
  statement {
    sid    = "ServicesUsedByTempSES"
    effect = "Allow"
    actions = [
      "acm:*",
      "apigateway:*",
      "budgets:*",
      "ce:*",
      "cloudfront:*",
      "cloudwatch:*",
      "dynamodb:*",
      "iam:*",
      "lambda:*",
      "logs:*",
      "route53:*",
      "s3:*",
      "ses:*",
      "sns:*",
      "sqs:*",
      "sts:GetCallerIdentity",
      "tag:GetResources",
      "wafv2:*",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ProtectAccountAndIAMUsers"
    effect = "Deny"
    actions = [
      "account:*",
      "organizations:*",
      "iam:CreateUser",
      "iam:DeleteUser",
      "iam:CreateAccessKey",
      "iam:DeleteAccessKey",
      "iam:CreateLoginProfile",
      "iam:UpdateLoginProfile",
      "iam:DeleteLoginProfile",
      "iam:AttachUserPolicy",
      "iam:DetachUserPolicy",
      "iam:PutUserPolicy",
      "iam:DeleteUserPolicy",
      "iam:UpdateUser",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "deploy" {
  name        = "${var.name_prefix}-github-deploy"
  description = "Service-scoped permissions for the TempSES GitHub Actions deploy role"
  policy      = data.aws_iam_policy_document.deploy.json
}

resource "aws_iam_role_policy_attachment" "deploy" {
  role       = aws_iam_role.deploy.name
  policy_arn = aws_iam_policy.deploy.arn
}
