locals {
  ghsa_github_token_secret_name = "opslens/dev/ghsa/github-token"
}

resource "aws_secretsmanager_secret" "ghsa_github_token" {
  # checkov:skip=CKV_AWS_149: ADR-0007 accepts the AWS-managed aws/secretsmanager KMS key for this single-account dev token; no customer-managed key requirement exists.
  # checkov:skip=CKV2_AWS_57: Automatic rotation is intentionally deferred for this dev-only GitHub credential. GitHub is not an AWS Secrets Manager managed-external-secret partner; rotating this credential would require external GitHub credential lifecycle logic. The token is populated out of band and must use a bounded GitHub expiration.

  name = local.ghsa_github_token_secret_name

  description = (
    "GitHub token used by the OpsLens dev GHSA Bronze ingestion runtime."
  )

  recovery_window_in_days = 7

  tags = {
    Purpose = "ghsa-ingestion-credential"
  }
}

output "ghsa_github_token_secret_arn" {
  description = "ARN of the GHSA GitHub token secret container."
  value       = aws_secretsmanager_secret.ghsa_github_token.arn
}
