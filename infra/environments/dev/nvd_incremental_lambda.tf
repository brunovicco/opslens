locals {
  nvd_incremental_lambda_artifact_path = (
    "${path.module}/../../../dist/opslens-nvd-incremental.zip"
  )
}

resource "aws_lambda_function" "nvd_incremental" {
  # checkov:skip=CKV_AWS_173: Lambda environment contains only non-secret NVD runtime configuration; a customer-managed KMS key is not justified.
  # checkov:skip=CKV_AWS_116: This phase uses explicit synchronous manual invocation; failures are returned directly to the caller before asynchronous scheduling is introduced.
  # checkov:skip=CKV_AWS_272: Lambda code signing is deferred until the project introduces an artifact signing and release trust workflow.
  # checkov:skip=CKV_AWS_117: The function requires outbound access to the public NVD endpoint and no private VPC resources; a VPC would add unnecessary NAT/network complexity.
  # checkov:skip=CKV_AWS_115: Reserved concurrency is deferred until scheduled operation; the current phase uses controlled synchronous manual invocation.

  function_name = local.nvd_incremental_lambda_function_name

  description = (
    "Ingest one authoritative bounded NVD CVE incremental window into immutable Bronze evidence."
  )

  role = aws_iam_role.nvd_incremental_lambda.arn

  runtime       = "python3.13"
  architectures = ["x86_64"]

  handler = (
    "opslens.ingestion.nvd.incremental_lambda_handler.lambda_handler"
  )

  filename = (
    local.nvd_incremental_lambda_artifact_path
  )

  source_code_hash = filebase64sha256(
    local.nvd_incremental_lambda_artifact_path
  )

  memory_size = 1024
  timeout     = 300

  environment {
    variables = {
      NVD_DATA_BUCKET = aws_s3_bucket.data.bucket

      NVD_WATERMARK_KEY = (
        "control/nvd/cve/incremental/watermark.json"
      )

      NVD_INCREMENTAL_BRONZE_PREFIX = (
        "bronze/nvd/cve/updates"
      )

      NVD_CVE_API_BASE_URL = (
        "https://services.nvd.nist.gov/rest/json/cves/2.0"
      )

      NVD_CVE_API_TIMEOUT_SECONDS = "30"

      NVD_CVE_API_MAX_RESPONSE_BYTES = "16777216"

      NVD_CVE_API_MINIMUM_INTERVAL_SECONDS = "6"

      NVD_CVE_API_MAX_ATTEMPTS = "3"
    }
  }

  tracing_config {
    mode = "Active"
  }

  logging_config {
    log_format            = "JSON"
    application_log_level = "INFO"
    system_log_level      = "INFO"
    log_group             = aws_cloudwatch_log_group.nvd_incremental.name
  }

  tags = {
    Purpose = "nvd-incremental"
  }

  depends_on = [
    aws_cloudwatch_log_group.nvd_incremental,
    aws_iam_role_policy.nvd_incremental_lambda_runtime,
  ]
}

output "nvd_incremental_lambda_function_arn" {
  description = "ARN of the NVD incremental ingestion Lambda function."
  value       = aws_lambda_function.nvd_incremental.arn
}
