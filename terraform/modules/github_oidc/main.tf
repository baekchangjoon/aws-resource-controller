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

# Deploy role: broad on this single-app account. For a shared account
# this should be tightened (per-service policies).
resource "aws_iam_role" "deploy" {
  name                 = "${var.name_prefix}-github-deploy"
  assume_role_policy   = data.aws_iam_policy_document.assume.json
  max_session_duration = 3600
}

# For a learning/personal account this is acceptable; for prod we would
# replace with a per-service policy.
resource "aws_iam_role_policy_attachment" "deploy_admin" {
  role       = aws_iam_role.deploy.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}
