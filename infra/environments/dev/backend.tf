terraform {
  backend "s3" {
    bucket       = "opslens-dev-tfstate-487757851499-us-east-1"
    key          = "environments/dev/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
