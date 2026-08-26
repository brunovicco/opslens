locals {
  nvd_promotion_lambda_function_name       = "opslens-dev-nvd-promotion"
  nvd_promotion_lambda_execution_role_name = "OpsLensNvdPromotionLambdaRole"

  nvd_promotion_lambda_log_group_name = (
    "/aws/lambda/${local.nvd_promotion_lambda_function_name}"
  )

  nvd_promotion_lambda_log_group_arn = (
    "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:${local.nvd_promotion_lambda_log_group_name}"
  )

  nvd_promotion_silver_incremental_object_arn = (
    "${aws_s3_bucket.data.arn}/silver/nvd/cve/schema_version=1/source_kind=incremental/*"
  )

  nvd_promotion_watermark_object_arn = (
    "${aws_s3_bucket.data.arn}/control/nvd/cve/incremental/watermark.json"
  )
}

data "aws_iam_policy_document" "nvd_promotion_lambda_assume_role" {
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

resource "aws_iam_role" "nvd_promotion_lambda" {
  name = local.nvd_promotion_lambda_execution_role_name

  description = (
    "Execution role for the OpsLens authoritative NVD watermark promotion Lambda."
  )

  assume_role_policy = (
    data.aws_iam_policy_document.nvd_promotion_lambda_assume_role.json
  )

  tags = {
    Purpose = "nvd-promotion-runtime"
  }
}

data "aws_iam_policy_document" "nvd_promotion_lambda_runtime" {
  statement {
    sid    = "ReadExactNvdSilverPromotionEvidence"
    effect = "Allow"

    actions = [
      "s3:GetObjectVersion",
    ]

    resources = [
      local.nvd_promotion_silver_incremental_object_arn,
    ]
  }

  statement {
    sid    = "ReadAuthoritativeNvdWatermark"
    effect = "Allow"

    actions = [
      "s3:GetObject",
    ]

    resources = [
      local.nvd_promotion_watermark_object_arn,
    ]
  }

  statement {
    sid    = "CommitAuthoritativeNvdWatermark"
    effect = "Allow"

    actions = [
      "s3:PutObject",
    ]

    resources = [
      local.nvd_promotion_watermark_object_arn,
    ]
  }

  statement {
    sid    = "SendNvdPromotionFailureRecords"
    effect = "Allow"

    actions = [
      "sqs:SendMessage",
    ]

    resources = [
      aws_sqs_queue.nvd_promotion_failures.arn,
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
      "${local.nvd_promotion_lambda_log_group_arn}:*",
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

resource "aws_iam_role_policy" "nvd_promotion_lambda_runtime" {
  name = "OpsLensNvdPromotionRuntimeAccess"
  role = aws_iam_role.nvd_promotion_lambda.id

  policy = (
    data.aws_iam_policy_document.nvd_promotion_lambda_runtime.json
  )
}

output "nvd_promotion_lambda_execution_role_arn" {
  description = "ARN of the NVD promotion Lambda execution role."
  value       = aws_iam_role.nvd_promotion_lambda.arn
}
