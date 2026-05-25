# addresses: PK=address, TTL=ttl_at
resource "aws_dynamodb_table" "addresses" {
  name         = "${var.name_prefix}-addresses"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "address"

  attribute {
    name = "address"
    type = "S"
  }

  ttl {
    enabled        = true
    attribute_name = "ttl_at"
  }

  point_in_time_recovery {
    enabled = false
  }

  tags = {
    Component = "addresses"
  }
}

# messages: PK=address, SK=message_id (ULID), TTL=ttl_at
resource "aws_dynamodb_table" "messages" {
  name         = "${var.name_prefix}-messages"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "address"
  range_key    = "message_id"

  attribute {
    name = "address"
    type = "S"
  }

  attribute {
    name = "message_id"
    type = "S"
  }

  ttl {
    enabled        = true
    attribute_name = "ttl_at"
  }

  point_in_time_recovery {
    enabled = false
  }

  tags = {
    Component = "messages"
  }
}
