provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = "tempses"
      Environment = "dev"
      ManagedBy   = "terraform"
    }
  }
}

# us-east-1 provider — ACM for CloudFront must be issued in us-east-1
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = {
      Project     = "tempses"
      Environment = "dev"
      ManagedBy   = "terraform"
    }
  }
}
