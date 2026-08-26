locals {
  nvd_promotion_artifact_sha256 = (
    "96cdffa2ec940f66bce800df00aaac93274445e250f1308ef9f1f37e6684a485"
  )

  nvd_promotion_artifact_sha256_base64 = (
    "ls3/ouyUD2a86ADfAKqskydEReJQ8TCO+fHzfmaEpIU="
  )

  nvd_promotion_artifact_key = (
    "lambda/nvd-promotion/${local.nvd_promotion_artifact_sha256}.zip"
  )

  nvd_promotion_artifact_version = (
    "jVFZJdhmtR9hQFCr90m3RxIoKN3.v05e"
  )
}

resource "aws_lambda_function" "nvd_promotion" {
  # checkov:skip=CKV_AWS_173: Lambda environment contains only non-secret S3 control-plane coordinates; a customer-managed KMS key is not justified for this dev workload.
  # checkov:skip=CKV_AWS_116: Asynchronous failures use an explicit Lambda OnFailure SQS destination configured through aws_lambda_function_event_invoke_config rather than dead_letter_config.
  # checkov:skip=CKV_AWS_272: Lambda code signing is deferred until the project introduces an artifact signing and release trust workflow.
  # checkov:skip=CKV_AWS_117: The function accesses public AWS S3 APIs and no private VPC resources; placing it in a VPC would add networking complexity without a current requirement.
  # checkov:skip=CKV_AWS_115: Reserved concurrency cannot be configured while the dev account regional Lambda concurrency quota does not support the existing workload isolation pattern; correctness is enforced by the authoritative S3 If-Match CAS.

  function_name = local.nvd_promotion_lambda_function_name

  description = (
    "Promote exact verified NVD Silver COMPLETE evidence to the authoritative incremental watermark using S3 CAS."
  )

  role = aws_iam_role.nvd_promotion_lambda.arn

  runtime       = "python3.13"
  architectures = ["x86_64"]

  handler = (
    "opslens.transformation.nvd.promotion_lambda_handler.lambda_handler"
  )

  s3_bucket         = aws_s3_bucket.deployment_artifacts.bucket
  s3_key            = local.nvd_promotion_artifact_key
  s3_object_version = local.nvd_promotion_artifact_version

  source_code_hash = local.nvd_promotion_artifact_sha256_base64

  memory_size = 1024
  timeout     = 120

  ephemeral_storage {
    size = 512
  }

  environment {
    variables = {
      NVD_DATA_BUCKET = aws_s3_bucket.data.bucket

      NVD_WATERMARK_KEY = (
        "control/nvd/cve/incremental/watermark.json"
      )
    }
  }

  tracing_config {
    mode = "Active"
  }

  logging_config {
    log_format            = "JSON"
    application_log_level = "INFO"
    system_log_level      = "INFO"
    log_group             = aws_cloudwatch_log_group.nvd_promotion.name
  }

  tags = {
    Purpose = "nvd-promotion"
  }

  depends_on = [
    aws_cloudwatch_log_group.nvd_promotion,
    aws_iam_role_policy.nvd_promotion_lambda_runtime,
  ]
}

resource "aws_lambda_function_event_invoke_config" "nvd_promotion" {
  function_name = aws_lambda_function.nvd_promotion.function_name

  maximum_event_age_in_seconds = 3600
  maximum_retry_attempts       = 2

  destination_config {
    on_failure {
      destination = aws_sqs_queue.nvd_promotion_failures.arn
    }
  }

  depends_on = [
    aws_iam_role_policy.nvd_promotion_lambda_runtime,
  ]
}

output "nvd_promotion_lambda_function_arn" {
  description = "ARN of the authoritative NVD watermark promotion Lambda."
  value       = aws_lambda_function.nvd_promotion.arn
}
