locals {
  ghsa_bronze_lambda_artifact_sha256 = (
    "9deb08f346cbe7261199568de8a515b26b2865d7f6d2a592d837a0ac0368c928"
  )

  ghsa_bronze_lambda_artifact_sha256_base64 = (
    "nesI80bL5yYRmVaN6KUVsmsoZdf20qWS2DegrANoySg="
  )

  ghsa_bronze_lambda_artifact_version = (
    "fYDkvIkv15n.GHoGCgOQbgcuFObO_P3w"
  )

  ghsa_bronze_lambda_artifact_key = (
    "lambda/ghsa-bronze/${local.ghsa_bronze_lambda_artifact_sha256}.zip"
  )
}

resource "aws_lambda_function" "ghsa_bronze" {
  # checkov:skip=CKV_AWS_173: Lambda environment contains only non-secret GHSA runtime configuration and a Secrets Manager identifier; no secret value is stored in environment variables.
  # checkov:skip=CKV_AWS_116: Phase 2.4C proves synchronous manual invocation first; no asynchronous invocation path exists yet, so a Lambda DLQ is not applicable.
  # checkov:skip=CKV_AWS_272: Lambda code signing is deferred until the project introduces an artifact signing and release trust workflow.
  # checkov:skip=CKV_AWS_117: The function requires outbound access to the public GitHub API and no private VPC resources; a VPC would add NAT/network complexity without a security requirement.
  # checkov:skip=CKV_AWS_115: Manual-only invocation keeps concurrency operator-bounded; reserved concurrency remains deferred because the dev account has previously constrained concurrency quota headroom.

  function_name = local.ghsa_bronze_lambda_function_name

  description = (
    "Ingest one explicit bounded GitHub Security Advisory window into immutable Bronze evidence."
  )

  role = aws_iam_role.ghsa_bronze_lambda.arn

  runtime       = "python3.13"
  architectures = ["x86_64"]

  handler = "opslens.ingestion.ghsa.lambda_handler.lambda_handler"

  s3_bucket         = aws_s3_bucket.deployment_artifacts.bucket
  s3_key            = local.ghsa_bronze_lambda_artifact_key
  s3_object_version = local.ghsa_bronze_lambda_artifact_version

  source_code_hash = local.ghsa_bronze_lambda_artifact_sha256_base64

  # The application may buffer up to 64 MiB of exact source bytes plus parsed
  # advisory models before persistence, so the minimum Lambda tier is avoided.
  memory_size = 1024
  timeout     = 900

  environment {
    variables = {
      GHSA_DATA_BUCKET = aws_s3_bucket.data.bucket

      GHSA_GITHUB_TOKEN_SECRET_ID = (
        aws_secretsmanager_secret.ghsa_github_token.arn
      )

      GHSA_BRONZE_PREFIX            = "bronze/ghsa/advisories"
      GHSA_HTTP_TIMEOUT_SECONDS     = "15"
      GHSA_HTTP_MAX_ATTEMPTS        = "3"
      GHSA_SECRET_CACHE_TTL_SECONDS = "300"
      GHSA_MAX_LEAF_WINDOWS         = "64"
    }
  }

  tracing_config {
    mode = "Active"
  }

  logging_config {
    log_format            = "JSON"
    application_log_level = "INFO"
    system_log_level      = "INFO"
    log_group             = aws_cloudwatch_log_group.ghsa_bronze.name
  }

  tags = {
    Purpose = "ghsa-bronze-ingestion"
  }

  depends_on = [
    aws_cloudwatch_log_group.ghsa_bronze,
    aws_iam_role_policy.ghsa_bronze_lambda_runtime,
  ]
}

output "ghsa_bronze_lambda_function_arn" {
  description = "ARN of the GHSA Bronze ingestion Lambda function."
  value       = aws_lambda_function.ghsa_bronze.arn
}
