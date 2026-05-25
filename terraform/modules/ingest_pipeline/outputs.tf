output "mail_bucket_name" {
  value = aws_s3_bucket.mail.bucket
}

output "mail_bucket_arn" {
  value = aws_s3_bucket.mail.arn
}

output "dlq_arn" {
  value = aws_sqs_queue.ingest_dlq.arn
}

output "dlq_url" {
  value = aws_sqs_queue.ingest_dlq.url
}

output "ingest_lambda_role_arn" {
  value = aws_iam_role.ingest_lambda.arn
}

output "ingest_lambda_role_name" {
  value = aws_iam_role.ingest_lambda.name
}

output "ingest_lambda_arn" {
  value = aws_lambda_function.ingest.arn
}

output "ingest_lambda_function_name" {
  value = aws_lambda_function.ingest.function_name
}
