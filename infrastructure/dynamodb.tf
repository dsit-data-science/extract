resource "aws_dynamodb_table" "dynamodb_responses_data" {
  name         = var.RESPONSES_TABLE_NAME
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "response_id"

  attribute {
    name = "response_id"
    type = "S"
  }

  tags = {
    Name = var.tag_name
  }
}

resource "aws_dynamodb_table" "dynamodb_review_data" {
  name         = var.REVIEW_TABLE_NAME
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "response_id"
  range_key    = "question_label"

  attribute {
    name = "response_id"
    type = "S"
  }
  attribute {
    name = "question_label"
    type = "S"
  }

  tags = {
    Name = var.tag_name
  }
}

resource "aws_dynamodb_table" "dynamodb_manual_review_data" {
  name         = var.MANUAL_TABLE_NAME
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "response_id"
  range_key    = "question_label"

  attribute {
    name = "response_id"
    type = "S"
  }
  attribute {
    name = "question_label"
    type = "S"
  }

  tags = {
    Name = var.tag_name
  }
}

resource "aws_dynamodb_table" "dynamodb_questions_data" {
  name         = var.QUESTIONS_TABLE_NAME
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "response_id"
  range_key    = "question_label"

  attribute {
    name = "response_id"
    type = "S"
  }
  attribute {
    name = "question_label"
    type = "S"
  }

  tags = {
    Name = var.tag_name
  }
}