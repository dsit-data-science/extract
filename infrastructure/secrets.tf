resource "aws_secretsmanager_secret" "app_secrets" {
  name        = "extract-secrets"
  description = "Secrets for the Extract application"
}