locals {
  epss_lambda_artifact_path = "${path.module}/../../../dist/opslens-epss-ingestion.zip"
}

resource "aws_lambda_function" "epss_ingestion" {
  function_name = local.epss_lambda_function_name
  description   = "Ingest FIRST EPSS snapshots into the OpsLens Bronze data lake."

  role = aws_iam_role.epss_ingestion_lambda.arn

  runtime       = "python3.13"
  architectures = ["x86_64"]

  handler = "opslens.ingestion.epss.lambda_handler.lambda_handler"

  filename         = local.epss_lambda_artifact_path
  source_code_hash = filebase64sha256(local.epss_lambda_artifact_path)

  memory_size = 512
  timeout     = 60

  environment {
    variables = {
      EPSS_SOURCE_URL           = "https://epss.empiricalsecurity.com/epss_scores-current.csv.gz"
      EPSS_BRONZE_BUCKET        = aws_s3_bucket.data.bucket
      EPSS_BRONZE_PREFIX        = "bronze/epss"
      EPSS_HTTP_TIMEOUT_SECONDS = "15"
    }
  }

  tracing_config {
    mode = "Active"
  }

  logging_config {
    log_format            = "JSON"
    application_log_level = "INFO"
    system_log_level      = "INFO"
    log_group             = aws_cloudwatch_log_group.epss_ingestion.name
  }

  tags = {
    Purpose = "epss-ingestion"
  }

  depends_on = [
    aws_cloudwatch_log_group.epss_ingestion,
    aws_iam_role_policy.epss_lambda_runtime,
  ]
}

output "epss_lambda_function_arn" {
  description = "ARN of the EPSS ingestion Lambda function."
  value       = aws_lambda_function.epss_ingestion.arn
}
