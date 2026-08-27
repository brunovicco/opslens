locals {
  nvd_analytics_projector_lambda_function_name       = "opslens-dev-nvd-analytics-projector"
  nvd_analytics_projector_lambda_execution_role_name = "OpsLensNvdAnalyticsProjectorLambdaRole"

  nvd_analytics_projector_lambda_log_group_name = (
    "/aws/lambda/${local.nvd_analytics_projector_lambda_function_name}"
  )

  nvd_analytics_projector_lambda_log_group_arn = (
    "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:${local.nvd_analytics_projector_lambda_log_group_name}"
  )

  nvd_analytics_projector_watermark_object_arn = (
    "${aws_s3_bucket.data.arn}/control/nvd/cve/incremental/watermark.json"
  )

  nvd_analytics_projector_silver_bootstrap_object_arn = (
    "${aws_s3_bucket.data.arn}/silver/nvd/cve/schema_version=1/source_kind=bootstrap/*"
  )

  nvd_analytics_projector_silver_incremental_object_arn = (
    "${aws_s3_bucket.data.arn}/silver/nvd/cve/schema_version=1/source_kind=incremental/*"
  )

  nvd_analytics_projector_destination_object_arn = (
    "${aws_s3_bucket.data.arn}/analytics/nvd/cve/schema_version=1/*"
  )
}

data "aws_iam_policy_document" "nvd_analytics_projector_lambda_assume_role" {
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

resource "aws_iam_role" "nvd_analytics_projector_lambda" {
  name = local.nvd_analytics_projector_lambda_execution_role_name

  description = (
    "Execution role for the OpsLens permanent NVD analytics projection Lambda."
  )

  assume_role_policy = (
    data.aws_iam_policy_document.nvd_analytics_projector_lambda_assume_role.json
  )

  tags = {
    Purpose = "nvd-analytics-projector-runtime"
  }
}

data "aws_iam_policy_document" "nvd_analytics_projector_lambda_runtime" {
  statement {
    sid    = "ReadExactNvdAnalyticsAuthority"
    effect = "Allow"

    actions = [
      "s3:GetObjectVersion",
    ]

    resources = [
      local.nvd_analytics_projector_watermark_object_arn,
      local.nvd_analytics_projector_silver_bootstrap_object_arn,
      local.nvd_analytics_projector_silver_incremental_object_arn,
    ]
  }

  statement {
    sid    = "ReadExactNvdAnalyticsProjection"
    effect = "Allow"

    actions = [
      "s3:GetObjectVersion",
    ]

    resources = [
      local.nvd_analytics_projector_destination_object_arn,
    ]
  }

  statement {
    sid    = "ReadCurrentNvdAnalyticsProjectionForReplay"
    effect = "Allow"

    actions = [
      "s3:GetObject",
    ]

    resources = [
      local.nvd_analytics_projector_destination_object_arn,
    ]
  }

  statement {
    sid    = "WriteNvdAnalyticsProjection"
    effect = "Allow"

    actions = [
      "s3:PutObject",
    ]

    resources = [
      local.nvd_analytics_projector_destination_object_arn,
    ]
  }

  statement {
    sid    = "SendNvdAnalyticsProjectorFailureRecords"
    effect = "Allow"

    actions = [
      "sqs:SendMessage",
    ]

    resources = [
      aws_sqs_queue.nvd_analytics_projector_failures.arn,
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
      "${local.nvd_analytics_projector_lambda_log_group_arn}:*",
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

resource "aws_iam_role_policy" "nvd_analytics_projector_lambda_runtime" {
  name = "OpsLensNvdAnalyticsProjectorRuntimeAccess"
  role = aws_iam_role.nvd_analytics_projector_lambda.id

  policy = (
    data.aws_iam_policy_document.nvd_analytics_projector_lambda_runtime.json
  )
}

output "nvd_analytics_projector_lambda_execution_role_arn" {
  description = "ARN of the permanent NVD analytics projector Lambda execution role."
  value       = aws_iam_role.nvd_analytics_projector_lambda.arn
}
