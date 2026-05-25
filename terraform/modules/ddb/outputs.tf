output "addresses_table_name" {
  value = aws_dynamodb_table.addresses.name
}

output "addresses_table_arn" {
  value = aws_dynamodb_table.addresses.arn
}

output "messages_table_name" {
  value = aws_dynamodb_table.messages.name
}

output "messages_table_arn" {
  value = aws_dynamodb_table.messages.arn
}
