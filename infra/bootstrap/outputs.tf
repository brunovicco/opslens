output "terraform_state_bucket" {
  description = "S3 bucket used for OpsLens Terraform remote state."
  value       = aws_s3_bucket.terraform_state.id
}

output "terraform_state_bucket_region" {
  description = "AWS Region containing the Terraform state bucket."
  value       = var.aws_region
}
