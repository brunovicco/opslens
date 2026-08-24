locals {
  nvd_silver_artifact_sha256 = (
    "185c2d609575de8cf230e1bc1cc4d73917caca39e9136a7486bffe9ef05e486e"
  )

  nvd_silver_artifact_sha256_base64 = (
    "GFwtYJV13ozyMOG8HMTXORfKyjnpE2p0hr/+nvBeSG4="
  )

  nvd_silver_artifact_key = (
    "lambda/nvd-silver/${local.nvd_silver_artifact_sha256}.zip"
  )

  nvd_silver_artifact_version = (
    "bbGNEJvJcfSKiW5fzDUwUnwR6ZOtf.A_"
  )
}

resource "aws_lambda_function" "nvd_silver" {
  # checkov:skip=CKV_AWS_173: Lambda environment contains only non-secret S3 configuration; a customer-managed KMS key is not justified for this dev NVD Silver workload.
  # checkov:skip=CKV_AWS_116: Asynchronous failures use an explicit Lambda OnFailure SQS destination configured through aws_lambda_function_event_invoke_config rather than dead_letter_config.
  # checkov:skip=CKV_AWS_272: Lambda code signing is deferred until the project introduces an artifact signing and release trust workflow.
  # checkov:skip=CKV_AWS_117: The function accesses AWS S3 APIs and no private VPC resources; placing it in a VPC would add networking complexity without a current requirement.
  # checkov:skip=CKV_AWS_115: Reserved concurrency cannot be configured while the dev account regional Lambda concurrency quota does not support the existing workload isolation pattern; NVD Silver is bounded, idempotent, and low-frequency.

  function_name = local.nvd_silver_lambda_function_name
  description   = "Transform exact OpsLens NVD Bronze COMPLETE evidence into deterministic Silver CVE version artifacts."

  role = aws_iam_role.nvd_silver_lambda.arn

  runtime       = "python3.13"
  architectures = ["x86_64"]

  handler = "opslens.transformation.nvd.lambda_handler.lambda_handler"

  s3_bucket         = aws_s3_bucket.deployment_artifacts.bucket
  s3_key            = local.nvd_silver_artifact_key
  s3_object_version = local.nvd_silver_artifact_version

  source_code_hash = local.nvd_silver_artifact_sha256_base64

  # The current dev account Lambda memory profile is capped at
  # 3008 MB. Re-evaluate after the real NVD Silver workload smoke
  # and after AWS raises the account memory quota.
  memory_size = 3008
  timeout     = 180

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
    log_group             = aws_cloudwatch_log_group.nvd_silver.name
  }

  tags = {
    Purpose = "nvd-silver"
  }

  depends_on = [
    aws_cloudwatch_log_group.nvd_silver,
    aws_iam_role_policy.nvd_silver_lambda_runtime,
  ]
}

output "nvd_silver_lambda_function_arn" {
  description = "ARN of the NVD Silver transformation Lambda function."
  value       = aws_lambda_function.nvd_silver.arn
}

resource "aws_lambda_function_event_invoke_config" "nvd_silver" {
  function_name = aws_lambda_function.nvd_silver.function_name

  maximum_event_age_in_seconds = 3600
  maximum_retry_attempts       = 2

  destination_config {
    on_failure {
      destination = aws_sqs_queue.nvd_silver_failures.arn
    }
  }

  depends_on = [
    aws_iam_role_policy.nvd_silver_lambda_runtime,
  ]
}
