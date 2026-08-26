variable "nvd_analytics_projector_artifact_sha256" {
  description = "Lowercase SHA-256 hex digest of the immutable NVD analytics projector deployment package."
  type        = string
  nullable    = false

  validation {
    condition = can(
      regex(
        "^[0-9a-f]{64}$",
        var.nvd_analytics_projector_artifact_sha256,
      )
    )
    error_message = "nvd_analytics_projector_artifact_sha256 must be a lowercase SHA-256 hex digest."
  }
}

variable "nvd_analytics_projector_artifact_sha256_base64" {
  description = "Base64-encoded SHA-256 digest of the immutable NVD analytics projector deployment package."
  type        = string
  nullable    = false

  validation {
    condition = can(
      regex(
        "^[A-Za-z0-9+/]{43}=$",
        var.nvd_analytics_projector_artifact_sha256_base64,
      )
    )
    error_message = "nvd_analytics_projector_artifact_sha256_base64 must encode one SHA-256 digest."
  }
}

variable "nvd_analytics_projector_artifact_version" {
  description = "Exact S3 VersionId of the immutable NVD analytics projector deployment package."
  type        = string
  nullable    = false

  validation {
    condition = (
      length(var.nvd_analytics_projector_artifact_version) > 0 &&
      trimspace(var.nvd_analytics_projector_artifact_version) == var.nvd_analytics_projector_artifact_version
    )
    error_message = "nvd_analytics_projector_artifact_version must be exact and non-empty."
  }
}

locals {
  nvd_analytics_projector_artifact_key = (
    "lambda/nvd-analytics-projector/${var.nvd_analytics_projector_artifact_sha256}.zip"
  )
}

resource "aws_lambda_function" "nvd_analytics_projector" {
  # checkov:skip=CKV_AWS_173: Lambda environment contains only a non-secret S3 data-bucket coordinate; a customer-managed KMS key is not justified for this dev workload.
  # checkov:skip=CKV_AWS_116: Asynchronous failures use an explicit Lambda OnFailure SQS destination configured through aws_lambda_function_event_invoke_config rather than dead_letter_config.
  # checkov:skip=CKV_AWS_272: Lambda code signing is deferred until the project introduces an artifact signing and release trust workflow.
  # checkov:skip=CKV_AWS_117: The function accesses public AWS S3 APIs and no private VPC resources; placing it in a VPC would add networking complexity without a current requirement.
  # checkov:skip=CKV_AWS_115: Reserved concurrency cannot be configured while the dev account regional Lambda concurrency quota does not support the existing workload isolation pattern; deterministic destinations and conditional writes preserve correctness under concurrent delivery.

  function_name = local.nvd_analytics_projector_lambda_function_name

  description = (
    "Project exact authorized NVD Silver Parquet versions into the permanent clean analytics namespace."
  )

  role = aws_iam_role.nvd_analytics_projector_lambda.arn

  runtime       = "python3.13"
  architectures = ["x86_64"]

  handler = (
    "opslens.transformation.nvd.analytics_projection_lambda_handler.lambda_handler"
  )

  s3_bucket         = aws_s3_bucket.deployment_artifacts.bucket
  s3_key            = local.nvd_analytics_projector_artifact_key
  s3_object_version = var.nvd_analytics_projector_artifact_version

  source_code_hash = var.nvd_analytics_projector_artifact_sha256_base64

  memory_size = 1024
  timeout     = 120

  ephemeral_storage {
    size = 512
  }

  environment {
    variables = {
      NVD_DATA_BUCKET = aws_s3_bucket.data.bucket
    }
  }

  tracing_config {
    mode = "Active"
  }

  logging_config {
    log_format            = "JSON"
    application_log_level = "INFO"
    system_log_level      = "INFO"
    log_group             = aws_cloudwatch_log_group.nvd_analytics_projector.name
  }

  tags = {
    Purpose = "nvd-analytics-projector"
  }

  depends_on = [
    aws_cloudwatch_log_group.nvd_analytics_projector,
    aws_iam_role_policy.nvd_analytics_projector_lambda_runtime,
  ]
}

resource "aws_lambda_function_event_invoke_config" "nvd_analytics_projector" {
  function_name = aws_lambda_function.nvd_analytics_projector.function_name

  maximum_event_age_in_seconds = 3600
  maximum_retry_attempts       = 2

  destination_config {
    on_failure {
      destination = aws_sqs_queue.nvd_analytics_projector_failures.arn
    }
  }

  depends_on = [
    aws_iam_role_policy.nvd_analytics_projector_lambda_runtime,
  ]
}

output "nvd_analytics_projector_lambda_function_arn" {
  description = "ARN of the permanent NVD analytics projector Lambda."
  value       = aws_lambda_function.nvd_analytics_projector.arn
}
