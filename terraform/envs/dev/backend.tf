terraform {
  backend "s3" {
    bucket         = "tempses-tfstate-322242916220"
    key            = "envs/dev/terraform.tfstate"
    region         = "ap-northeast-2"
    dynamodb_table = "tempses-tflock"
    encrypt        = true
    profile        = "default"
  }
}
