terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.87.0"
    }
  }
  required_version = ">=1.2.0"

  backend "s3" {}
}

provider "aws" {
  region = var.aws_region
}
