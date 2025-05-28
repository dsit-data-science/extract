data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "s3_user_upload_data" {
  bucket = "${var.s3_user_upload_data_name}-${lower(var.ENVIRONMENT)}"

  tags = {
    Name = var.tag_name
  }
}

resource "aws_s3_bucket_versioning" "s3_user_upload_data_versioning" {
  bucket = aws_s3_bucket.s3_user_upload_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_policy" "s3_user_upload_data_policy" {
  bucket = aws_s3_bucket.s3_user_upload_data.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowUsersGetPutS3"
        Effect    = "Allow"
        Principal = "*"
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.s3_user_upload_data.arn}/*"
        Condition = {
          StringEquals = {
            "aws:PrincipalAccount" : data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
}