terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.82.0"
    }
  }

  # Uncomment to store state in S3 (recommended for team deployments):
  # backend "s3" {
  #   bucket  = "pdf-fillr-production"
  #   key     = "terraform-state/mapper/terraform.tfstate"
  #   region  = "us-east-1"
  #   encrypt = true
  # }
}

provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
