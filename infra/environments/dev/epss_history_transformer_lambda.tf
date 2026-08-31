locals {
  epss_history_transformer_artifact_path = (
    "${path.module}/../../../dist/opslens-epss-history-transformer.zip"
  )
  epss_history_transformer_artifact_sha256 = filesha256(
    local.epss_history_transformer_artifact_path
  )
  epss_history_transformer_artifact_key = (
    "lambda/epss-history-transformer/${local.epss_history_transformer_artifact_sha256}.zip"
  )
}

resource "aws_lambda_function" "epss_history_transformer" {
  # checkov:skip=CKV_AWS_173: Environment variables contain only non-secret bucket and immutable source-coordinate configuration.
  # checkov:skip=CKV_AWS_116: The D2 canary uses synchronous RequestResponse invocation; failures return directly to the bounded coordinator.
  # checkov:skip=CKV_AWS_272: Lambda code signing remains deferred until the project introduces an artifact-signing trust workflow.
  # checkov:skip=CKV_AWS_117: The transformer only accesses AWS APIs and no private VPC resources; VPC placement would add unnecessary networking complexity.
  # checkov:skip=CKV_AWS_115: The dev account previously exposed a regional concurrency quota too small to reserve concurrency without violating Lambda's unreserved-concurrency minimum. The D2 canary is instead fail-closed at coordinator concurrency 1.

  function_name = local.epss_history_transformer_function_name
  description   = "Transform one exact historical EPSS Bronze manifest into verified Silver evidence."

  role = aws_iam_role.epss_history_transformer.arn

  runtime       = "python3.13"
  architectures = ["x86_64"]
  handler       = "opslens.transformation.epss.history.lambda_handler.lambda_handler"

  s3_bucket = aws_s3_bucket.deployment_artifacts.bucket
  s3_key    = local.epss_history_transformer_artifact_key

  source_code_hash = filebase64sha256(local.epss_history_transformer_artifact_path)

  memory_size = 1024
  timeout     = 120

  environment {
    variables = {
      EPSS_DATA_BUCKET            = aws_s3_bucket.data.bucket
      EPSS_HISTORY_ARCHIVE_COMMIT = "7ba701f5599057c496489ceecd701cbd43911f5c"
    }
  }

  tracing_config {
    mode = "Active"
  }

  logging_config {
    log_format            = "JSON"
    application_log_level = "INFO"
    system_log_level      = "INFO"
    log_group             = aws_cloudwatch_log_group.epss_history_transformer.name
  }

  tags = {
    Purpose = "epss-history-transformer"
  }

  depends_on = [
    aws_cloudwatch_log_group.epss_history_transformer,
    aws_iam_role_policy.epss_history_transformer_runtime,
  ]
}

output "epss_history_transformer_function_arn" {
  description = "ARN of the bounded historical EPSS transformer Lambda."
  value       = aws_lambda_function.epss_history_transformer.arn
}

output "epss_history_transformer_function_name" {
  description = "Name of the bounded historical EPSS transformer Lambda."
  value       = aws_lambda_function.epss_history_transformer.function_name
}
