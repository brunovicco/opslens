provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "opslens"
      Environment = "dev"
      ManagedBy   = "terraform"
      Repository  = "brunovicco/opslens"
    }
  }
}
