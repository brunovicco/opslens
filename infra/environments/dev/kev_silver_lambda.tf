locals {
  kev_silver_artifact_sha256 = (
    "91f6034c678f30f0ed5aae0f81c011e5f1748a82b2cb179f010f69f7d21dfc5f"
  )

  kev_silver_artifact_sha256_base64 = (
    "kfYDTGePMPDtWq4PgcAR5fF0ioKyyxefAQ9p99Id/F8="
  )

  kev_silver_artifact_key = (
    "lambda/kev-silver/${local.kev_silver_artifact_sha256}.zip"
  )

  kev_silver_artifact_version = (
    "rKKEb2QL2VeCeD8Kts0AnTxdSz2y3VPi"
  )
}

resource "aws_lambda_function" "kev_silver" {
  # checkov:skip=CKV_AWS_173: Lambda environment contains only non-secret S3 configuration; a customer-managed KMS key is not justified for the dev KEV Silver workload.
  # checkov:skip=CKV_AWS_116: Asynchronous failures will use a Lambda OnFailure SQS destination rather than a traditional Lambda DLQ; event wiring is intentionally introduced after the isolated runtime gate.
  # checkov:skip=CKV_AWS_272: Lambda code signing is deferred until the project introduces an artifact signing and release trust workflow.
  # checkov:skip=CKV_AWS_117: The function accesses AWS S3 APIs and no private VPC resources; placing it in a VPC would add networking complexity without a current requirement.
  # checkov:skip=CKV_AWS_115: Reserved concurrency cannot be configured while the dev account regional Lambda concurrency quota does not support the existing workload isolation pattern; KEV Silver is low-volume and idempotent.

  function_name = local.kev_silver_lambda_function_name
  description   = "Transform OpsLens CISA KEV Bronze snapshots into normalized Silver Parquet artifacts."

  role = aws_iam_role.kev_silver_lambda.arn

  runtime       = "python3.13"
  architectures = ["x86_64"]

  handler = "opslens.transformation.kev.lambda_handler.lambda_handler"

  s3_bucket         = aws_s3_bucket.deployment_artifacts.bucket
  s3_key            = local.kev_silver_artifact_key
  s3_object_version = local.kev_silver_artifact_version

  source_code_hash = local.kev_silver_artifact_sha256_base64

  memory_size = 1024
  timeout     = 60

  environment {
    variables = {
      KEV_DATA_BUCKET   = aws_s3_bucket.data.bucket
      KEV_SILVER_PREFIX = "silver/kev"
    }
  }

  tracing_config {
    mode = "Active"
  }

  logging_config {
    log_format            = "JSON"
    application_log_level = "INFO"
    system_log_level      = "INFO"
    log_group             = aws_cloudwatch_log_group.kev_silver.name
  }

  tags = {
    Purpose = "kev-silver"
  }

  depends_on = [
    aws_cloudwatch_log_group.kev_silver,
    aws_iam_role_policy.kev_silver_lambda_runtime,
  ]
}

output "kev_silver_lambda_function_arn" {
  description = "ARN of the KEV Silver transformation Lambda function."
  value       = aws_lambda_function.kev_silver.arn
}
