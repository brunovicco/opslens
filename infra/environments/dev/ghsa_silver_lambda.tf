locals {
  ghsa_silver_lambda_artifact_sha256 = (
    "242e6fe88efd09514fe70e4b1dd3ec3a4335884b6a80d4f8b943c5fa3f0ae27e"
  )

  ghsa_silver_lambda_artifact_sha256_base64 = (
    "JC5v6I79CVFP5w5LHdPsOkM1iEtqgNT4uUPF+j8K4n4="
  )

  ghsa_silver_lambda_artifact_version = (
    "Bb6ludDG1hI4ztxoK2xxQa9zxmLfqwde"
  )

  ghsa_silver_lambda_artifact_key = (
    "lambda/ghsa-silver/${local.ghsa_silver_lambda_artifact_sha256}.zip"
  )
}

resource "aws_lambda_function" "ghsa_silver" {
  # checkov:skip=CKV_AWS_173: Lambda environment contains only a non-secret S3 bucket name for public GHSA transformation data.
  # checkov:skip=CKV_AWS_116: Phase 2.4D proves synchronous manual invocation first; no asynchronous invocation path exists yet, so a Lambda DLQ is not applicable.
  # checkov:skip=CKV_AWS_272: Lambda code signing is deferred until the project introduces an artifact signing and release trust workflow.
  # checkov:skip=CKV_AWS_117: The function accesses AWS S3 APIs and no private VPC resources; placing it in a VPC would add networking complexity without a current requirement.
  # checkov:skip=CKV_AWS_115: Manual-only invocation keeps concurrency operator-bounded; reserved concurrency remains deferred because the dev account has previously constrained concurrency quota headroom.

  function_name = local.ghsa_silver_lambda_function_name

  description = (
    "Transform one exact GHSA Bronze COMPLETE manifest into immutable advisory-version Silver evidence."
  )

  role = aws_iam_role.ghsa_silver_lambda.arn

  runtime       = "python3.13"
  architectures = ["x86_64"]

  handler = "opslens.transformation.ghsa.lambda_handler.lambda_handler"

  s3_bucket         = aws_s3_bucket.deployment_artifacts.bucket
  s3_key            = local.ghsa_silver_lambda_artifact_key
  s3_object_version = local.ghsa_silver_lambda_artifact_version

  source_code_hash = local.ghsa_silver_lambda_artifact_sha256_base64

  # GHSA Silver uses PyArrow and may hold bounded Bronze pages, canonical
  # advisory models, and one-row Parquet artifacts during transformation.
  # Reuse the proven dev transformation memory tier until the live smoke
  # provides evidence for safely reducing it.
  memory_size = 3008
  timeout     = 900

  ephemeral_storage {
    size = 512
  }

  environment {
    variables = {
      GHSA_DATA_BUCKET = aws_s3_bucket.data.bucket
    }
  }

  tracing_config {
    mode = "Active"
  }

  logging_config {
    log_format            = "JSON"
    application_log_level = "INFO"
    system_log_level      = "INFO"
    log_group             = aws_cloudwatch_log_group.ghsa_silver.name
  }

  tags = {
    Purpose = "ghsa-silver"
  }

  depends_on = [
    aws_cloudwatch_log_group.ghsa_silver,
    aws_iam_role_policy.ghsa_silver_lambda_runtime,
  ]
}

output "ghsa_silver_lambda_function_arn" {
  description = "ARN of the GHSA Silver transformation Lambda function."
  value       = aws_lambda_function.ghsa_silver.arn
}
