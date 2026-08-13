provider "aws" {
  region = "us-east-1"

  default_tags {
    tags = {
      Project     = "opslens"
      Environment = "dev"
      ManagedBy   = "terraform"
      Repository  = "brunovicco/opslens"
    }
  }
}
