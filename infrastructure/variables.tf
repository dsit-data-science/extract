variable "aws_region" {
  type    = string
  default = "eu-west-2"
}

variable "tag_name" {
  type    = string
  default = "extract-app"
}

variable "terraform_backend_bucket" {
  type    = string
  default = "extract-terraform-state"
}

variable "s3_user_upload_data_name" {
  type    = string
  default = "extract-upload-data"
}

variable "dynamo_keys" {
  type = object({
    hash_key  = string
    range_key = string
  })
  description = "Keys for setting up DynamoDB"
  default = {
    hash_key  = "id"
    range_key = "processed_datetime"
  }
}

variable "MODEL_SECRETS_ID" {
  type      = string
  sensitive = true
}

variable "USER_UPLOAD_S3_BUCKET" {
  type = string
}

variable "SYSTEM_PROMPT_TEMPLATE_PATH" {
  type = string
}

variable "HUMAN_PROMPT_TEMPLATE_PATH" {
  type = string
}

variable "RESPONSES_TABLE_NAME" {
  type    = string
  default = "extract-responses"
}

variable "REVIEW_TABLE_NAME" {
  type    = string
  default = "extract-reviews"
}

variable "MANUAL_TABLE_NAME" {
  type    = string
  default = "extract-manual-reviews"
}

variable "QUESTIONS_TABLE_NAME" {
  type    = string
  default = "extract-questions"
}

variable "ENVIRONMENT" {
  type = string
}