######################################################################
# S3 bucket — stores SES raw emails (emails/) and attachments (attachments/)
######################################################################

resource "aws_s3_bucket" "mail" {
  bucket = "${var.name_prefix}-mail-${var.account_id}"
}

resource "aws_s3_bucket_public_access_block" "mail" {
  bucket                  = aws_s3_bucket.mail.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "mail" {
  bucket = aws_s3_bucket.mail.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "mail" {
  bucket = aws_s3_bucket.mail.id
  versioning_configuration {
    status = "Disabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "mail" {
  bucket = aws_s3_bucket.mail.id

  rule {
    id     = "expire-emails"
    status = "Enabled"
    filter { prefix = "emails/" }
    expiration { days = var.emails_expire_days }
  }

  rule {
    id     = "expire-attachments"
    status = "Enabled"
    filter { prefix = "attachments/" }
    expiration { days = var.attachments_expire_days }
  }
}

# Allow SES to put inbound emails into emails/ prefix
data "aws_iam_policy_document" "mail_bucket_policy" {
  statement {
    sid       = "AllowSESPutObject"
    effect    = "Allow"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.mail.arn}/emails/*"]

    principals {
      type        = "Service"
      identifiers = ["ses.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceAccount"
      values   = [var.account_id]
    }
  }
}

resource "aws_s3_bucket_policy" "mail" {
  bucket = aws_s3_bucket.mail.id
  policy = data.aws_iam_policy_document.mail_bucket_policy.json
}

######################################################################
# DLQ for ingest Lambda failures
######################################################################

resource "aws_sqs_queue" "ingest_dlq" {
  name                       = "${var.name_prefix}-ingest-dlq"
  message_retention_seconds  = 1209600 # 14 days
  visibility_timeout_seconds = 60
}

######################################################################
# IAM role for ingest Lambda
######################################################################

data "aws_iam_policy_document" "ingest_lambda_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ingest_lambda" {
  name               = "${var.name_prefix}-ingest-lambda"
  assume_role_policy = data.aws_iam_policy_document.ingest_lambda_assume.json
}

data "aws_iam_policy_document" "ingest_lambda" {
  statement {
    sid     = "Logs"
    effect  = "Allow"
    actions = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = [
      "arn:aws:logs:${var.region}:${var.account_id}:log-group:/aws/lambda/${var.name_prefix}-ingest*",
    ]
  }

  statement {
    sid    = "S3ReadEmails"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:GetObjectAttributes",
    ]
    resources = ["${aws_s3_bucket.mail.arn}/emails/*"]
  }

  statement {
    sid       = "S3WriteAttachments"
    effect    = "Allow"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.mail.arn}/attachments/*"]
  }

  statement {
    sid    = "DDB"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
    ]
    resources = [
      var.addresses_table_arn,
      var.messages_table_arn,
    ]
  }

  statement {
    sid       = "DLQ"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.ingest_dlq.arn]
  }
}

resource "aws_iam_role_policy" "ingest_lambda" {
  name   = "${var.name_prefix}-ingest-lambda"
  role   = aws_iam_role.ingest_lambda.id
  policy = data.aws_iam_policy_document.ingest_lambda.json
}
