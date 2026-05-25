terraform {
  backend "s3" {
    bucket         = "tempses-tfstate-322242916220"
    key            = "envs/dev/terraform.tfstate"
    region         = "ap-northeast-2"
    dynamodb_table = "tempses-tflock"
    encrypt        = true
    # No profile here — AWS credentials come from the default chain
    # (env vars in CI, named profile or SSO locally).
  }
}
