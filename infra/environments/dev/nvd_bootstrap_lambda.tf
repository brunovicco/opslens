locals {
  nvd_bootstrap_lambda_artifact_sha256 = (
    "4baa4ddc3a3d841eb9c0ca77fe10a8796dcd9bd1a444df8b06ad5a55f23db74e"
  )
  nvd_bootstrap_lambda_artifact_sha256_base64 = (
    "S6pN3Do9hB65wMp3/hCoeW3Nm9GkRN+LBq1aVfI9t04="
  )
  nvd_bootstrap_lambda_artifact_version = (
    "kHiC2lB3vu2c2Ta5mgRFmO85BuoUYz7D"
  )
  nvd_bootstrap_lambda_artifact_key = (
    "lambda/nvd-bootstrap-ingestion/${local.nvd_bootstrap_lambda_artifact_sha256}.zip"
  )
}

resource "aws_lambda_function" "nvd_bootstrap_ingestion" {
  # checkov:skip=CKV_AWS_173: Lambda environment contains only non-secret NVD runtime configuration; a customer-managed KMS key is not justified.
  # checkov:skip=CKV_AWS_116: This bootstrap proof uses explicit synchronous manual invocation; failures are returned directly to the caller rather than an asynchronous DLQ.
  # checkov:skip=CKV_AWS_272: Lambda code signing is deferred until the project introduces an artifact signing and release trust workflow.
  # checkov:skip=CKV_AWS_117: The function requires outbound access to the public NVD endpoint and no private VPC resources; a VPC would introduce unnecessary NAT/network complexity.
  # checkov:skip=CKV_AWS_115: Reserved concurrency is not required for the manually invoked idempotent dev bootstrap proof.

  function_name = local.nvd_bootstrap_lambda_function_name
  description   = "Bootstrap immutable NVD JSON 2.0 yearly-feed evidence into the OpsLens Bronze data lake."

  role = aws_iam_role.nvd_bootstrap_ingestion_lambda.arn

  runtime       = "python3.13"
  architectures = ["x86_64"]

  handler = "opslens.ingestion.nvd.lambda_handler.lambda_handler"

  s3_bucket         = aws_s3_bucket.deployment_artifacts.bucket
  s3_key            = local.nvd_bootstrap_lambda_artifact_key
  s3_object_version = local.nvd_bootstrap_lambda_artifact_version

  source_code_hash = local.nvd_bootstrap_lambda_artifact_sha256_base64

  memory_size = 1024
  timeout     = 180

  environment {
    variables = {
      NVD_SOURCE_BASE_URL = (
        "https://nvd.nist.gov/feeds/json/cve/2.0"
      )

      NVD_BRONZE_BUCKET        = aws_s3_bucket.data.bucket
      NVD_BRONZE_PREFIX        = "bronze/nvd/cve/bootstrap"
      NVD_HTTP_TIMEOUT_SECONDS = "30"
      NVD_MAX_META_BYTES       = "1048576"
      NVD_MAX_FEED_BYTES       = "134217728"
    }
  }

  tracing_config {
    mode = "Active"
  }

  logging_config {
    log_format            = "JSON"
    application_log_level = "INFO"
    system_log_level      = "INFO"
    log_group             = aws_cloudwatch_log_group.nvd_bootstrap_ingestion.name
  }

  tags = {
    Purpose = "nvd-bootstrap-ingestion"
  }

  depends_on = [
    aws_cloudwatch_log_group.nvd_bootstrap_ingestion,
    aws_iam_role_policy.nvd_bootstrap_lambda_runtime,
  ]
}

output "nvd_bootstrap_lambda_function_arn" {
  description = "ARN of the NVD Bootstrap ingestion Lambda function."
  value       = aws_lambda_function.nvd_bootstrap_ingestion.arn
}
