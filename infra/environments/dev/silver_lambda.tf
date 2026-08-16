locals {
  epss_silver_artifact_sha256 = "11ca2b6a7dda648438865c7f7b60aabd56870bc1324cc85b02ad5eb89c649fad"

  epss_silver_artifact_sha256_base64 = "Ecoran3aZIQ4hlx/e2CqvVaHC8EyTMhbAq1euJxkn60="

  epss_silver_artifact_key = (
    "lambda/epss-silver/${local.epss_silver_artifact_sha256}.zip"
  )

  epss_silver_artifact_version = "4TMrvu1rjevPIxCGvyt2D0ankZjSFYVm"
}

resource "aws_lambda_function" "epss_silver" {
  # checkov:skip=CKV_AWS_173: Lambda environment contains only non-secret S3 configuration; a customer-managed KMS key is not justified for the dev EPSS Silver workload.
  # checkov:skip=CKV_AWS_116:Asynchronous failures use a Lambda OnFailure SQS destination with enriched invocation records instead of a traditional Lambda DLQ.
  # checkov:skip=CKV_AWS_272: Lambda code signing is deferred until the project introduces an artifact signing and release trust workflow.
  # checkov:skip=CKV_AWS_117: The function accesses AWS S3 APIs and no private VPC resources; placing it in a VPC would add networking complexity without a current requirement.
  # checkov:skip=CKV_AWS_115: Reserved concurrency cannot be configured while the dev account regional Lambda concurrency quota is 10; AWS previously rejected a reservation of 1 because it would reduce unreserved concurrency below the account minimum.

  function_name = local.epss_silver_lambda_function_name
  description   = "Transform OpsLens EPSS Bronze snapshots into normalized Silver Parquet artifacts."

  role = aws_iam_role.epss_silver_lambda.arn

  runtime       = "python3.13"
  architectures = ["x86_64"]

  handler = "opslens.transformation.epss.lambda_handler.lambda_handler"

  s3_bucket         = aws_s3_bucket.deployment_artifacts.bucket
  s3_key            = local.epss_silver_artifact_key
  s3_object_version = local.epss_silver_artifact_version

  source_code_hash = local.epss_silver_artifact_sha256_base64

  memory_size = 1024
  timeout     = 60

  environment {
    variables = {
      EPSS_DATA_BUCKET   = aws_s3_bucket.data.bucket
      EPSS_SILVER_PREFIX = "silver/epss"
    }
  }

  tracing_config {
    mode = "Active"
  }

  logging_config {
    log_format            = "JSON"
    application_log_level = "INFO"
    system_log_level      = "INFO"
    log_group             = aws_cloudwatch_log_group.epss_silver.name
  }

  tags = {
    Purpose = "epss-silver"
  }

  depends_on = [
    aws_cloudwatch_log_group.epss_silver,
    aws_iam_role_policy.epss_silver_lambda_runtime,
  ]
}

output "epss_silver_lambda_function_arn" {
  description = "ARN of the EPSS Silver transformation Lambda function."
  value       = aws_lambda_function.epss_silver.arn
}
