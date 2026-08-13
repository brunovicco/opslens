output "terraform_state_bucket" {
  description = "S3 bucket used for OpsLens Terraform remote state."
  value       = aws_s3_bucket.terraform_state.id
}

output "terraform_state_bucket_region" {
  description = "AWS Region containing the Terraform state bucket."
  value       = var.aws_region
}

output "github_actions_oidc_provider_arn" {
  description = "ARN of the GitHub Actions OIDC provider."
  value       = aws_iam_openid_connect_provider.github_actions.arn
}

output "github_actions_deploy_role_arn" {
  description = "ARN of the IAM role assumed by OpsLens GitHub Actions."
  value       = aws_iam_role.github_actions_deploy.arn
}
