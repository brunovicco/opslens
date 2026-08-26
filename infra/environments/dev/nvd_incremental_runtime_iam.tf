locals {
  nvd_incremental_lambda_function_name = (
    "opslens-dev-nvd-incremental"
  )

  nvd_incremental_lambda_execution_role_name = (
    "OpsLensNvdIncrementalLambdaRole"
  )

  nvd_incremental_lambda_log_group_name = (
    "/aws/lambda/${local.nvd_incremental_lambda_function_name}"
  )

  nvd_incremental_lambda_log_group_arn = (
    "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:${local.nvd_incremental_lambda_log_group_name}"
  )

  nvd_incremental_watermark_object_arn = (
    "${aws_s3_bucket.data.arn}/control/nvd/cve/incremental/watermark.json"
  )

  nvd_incremental_bronze_object_arn = (
    "${aws_s3_bucket.data.arn}/bronze/nvd/cve/updates/*"
  )
}

data "aws_iam_policy_document" "nvd_incremental_lambda_assume_role" {
  statement {
    sid     = "AllowLambdaService"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type = "Service"

      identifiers = [
        "lambda.amazonaws.com",
      ]
    }
  }
}

resource "aws_iam_role" "nvd_incremental_lambda" {
  name = local.nvd_incremental_lambda_execution_role_name

  description = (
    "Execution role for the OpsLens authoritative NVD incremental ingestion Lambda."
  )

  assume_role_policy = (
    data.aws_iam_policy_document.nvd_incremental_lambda_assume_role.json
  )

  tags = {
    Purpose = "nvd-incremental-runtime"
  }
}

data "aws_iam_policy_document" "nvd_incremental_lambda_runtime" {
  statement {
    sid    = "ReadAuthoritativeNvdWatermark"
    effect = "Allow"

    actions = [
      "s3:GetObject",
    ]

    resources = [
      local.nvd_incremental_watermark_object_arn,
    ]
  }

  statement {
    sid    = "WriteAndVerifyNvdIncrementalBronze"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
    ]

    resources = [
      local.nvd_incremental_bronze_object_arn,
    ]
  }

  statement {
    sid    = "WriteLambdaLogs"
    effect = "Allow"

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = [
      "${local.nvd_incremental_lambda_log_group_arn}:*",
    ]
  }

  statement {
    sid    = "WriteXRayTelemetry"
    effect = "Allow"

    actions = [
      "xray:PutTelemetryRecords",
      "xray:PutTraceSegments",
    ]

    resources = [
      "*",
    ]
  }
}

resource "aws_iam_role_policy" "nvd_incremental_lambda_runtime" {
  name = "OpsLensNvdIncrementalRuntimeAccess"
  role = aws_iam_role.nvd_incremental_lambda.id

  policy = (
    data.aws_iam_policy_document.nvd_incremental_lambda_runtime.json
  )
}

output "nvd_incremental_lambda_execution_role_arn" {
  description = "ARN of the NVD incremental Lambda execution role."
  value       = aws_iam_role.nvd_incremental_lambda.arn
}
