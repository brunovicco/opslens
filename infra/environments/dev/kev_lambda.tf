locals {
  kev_lambda_artifact_path = "${path.module}/../../../dist/opslens-kev-ingestion.zip"
}

resource "aws_lambda_function" "kev_ingestion" {
  # checkov:skip=CKV_AWS_173: Lambda environment contains only non-secret configuration; a customer-managed KMS key is not justified for the dev KEV ingestion workload.
  # checkov:skip=CKV_AWS_116: Asynchronous failures use a Lambda OnFailure SQS destination with enriched invocation records instead of a traditional Lambda DLQ.
  # checkov:skip=CKV_AWS_272: Lambda code signing is deferred until the project introduces an artifact signing and release trust workflow.
  # checkov:skip=CKV_AWS_117: The function requires outbound access to the public CISA KEV endpoint and no private VPC resources; placing it in a VPC would add NAT/network complexity without a security requirement.
  # checkov:skip=CKV_AWS_115: Reserved concurrency is not configured because the dev account regional Lambda concurrency quota does not currently support the existing workload isolation pattern; the daily Scheduler invocation is bounded and ingestion is idempotent.

  function_name = local.kev_lambda_function_name
  description   = "Ingest CISA Known Exploited Vulnerabilities catalog snapshots into the OpsLens Bronze data lake."

  role = aws_iam_role.kev_ingestion_lambda.arn

  runtime       = "python3.13"
  architectures = ["x86_64"]

  handler = "opslens.ingestion.kev.lambda_handler.lambda_handler"

  filename         = local.kev_lambda_artifact_path
  source_code_hash = filebase64sha256(local.kev_lambda_artifact_path)

  memory_size = 512
  timeout     = 60

  environment {
    variables = {
      KEV_SOURCE_URL = (
        "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
      )

      KEV_BRONZE_BUCKET        = aws_s3_bucket.data.bucket
      KEV_BRONZE_PREFIX        = "bronze/kev"
      KEV_HTTP_TIMEOUT_SECONDS = "15"
      KEV_MAX_SOURCE_BYTES     = "10485760"
    }
  }

  tracing_config {
    mode = "Active"
  }

  logging_config {
    log_format            = "JSON"
    application_log_level = "INFO"
    system_log_level      = "INFO"
    log_group             = aws_cloudwatch_log_group.kev_ingestion.name
  }

  tags = {
    Purpose = "kev-ingestion"
  }

  depends_on = [
    aws_cloudwatch_log_group.kev_ingestion,
    aws_iam_role_policy.kev_lambda_runtime,
  ]
}

output "kev_lambda_function_arn" {
  description = "ARN of the CISA KEV ingestion Lambda function."
  value       = aws_lambda_function.kev_ingestion.arn
}
