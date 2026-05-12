provider "aws" {
    region = "us-east-1"
}

#Remote state locking
terraform {
  backend "s3" {
    bucket         = "gitops-state-bucket"
    key            = "gitops-mvp/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}