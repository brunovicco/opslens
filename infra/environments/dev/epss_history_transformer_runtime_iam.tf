locals {
  epss_history_transformer_function_name = "opslens-dev-epss-history-transformer"
  epss_history_transformer_role_name     = "OpsLensEpssHistoryTransformerLambdaRole"
  epss_history_transformer_log_group_name = (
    "/aws/lambda/${local.epss_history_transformer_function_name}"
  )
  epss_history_transformer_log_group_arn = (
    "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:${local.epss_history_transformer_log_group_name}"
  )

  epss_history_bronze_object_arn = "${aws_s3_bucket.data.arn}/bronze/epss-history/*"
  epss_history_silver_object_arn = (
    "${aws_s3_bucket.data.arn}/silver/epss/snapshot_date=*/part-00000.parquet"
  )
  epss_history_completion_object_arn = (
    "${aws_s3_bucket.data.arn}/silver/epss-history/completions/*"
  )
}

data "aws_iam_policy_document" "epss_history_transformer_assume_role" {
  statement {
    sid     = "AllowLambdaService"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "epss_history_transformer" {
  name        = local.epss_history_transformer_role_name
  description = "Execution role for the bounded OpsLens historical EPSS transformer Lambda."

  assume_role_policy = data.aws_iam_policy_document.epss_history_transformer_assume_role.json

  tags = {
    Purpose = "epss-history-transformer-runtime"
  }
}

data "aws_iam_policy_document" "epss_history_transformer_runtime" {
  statement {
    sid    = "DiscoverForwardEpssBoundary"
    effect = "Allow"

    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.data.arn]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["bronze/epss/*"]
    }
  }

  statement {
    sid    = "ReadExactHistoricalBronze"
    effect = "Allow"

    actions = [
      "s3:GetObjectVersion",
    ]

    resources = [
      local.epss_history_bronze_object_arn,
    ]
  }

  statement {
    sid    = "PersistAndVerifyHistoricalSilver"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:PutObject",
    ]

    resources = [
      local.epss_history_silver_object_arn,
    ]
  }

  statement {
    sid    = "PersistAndVerifyCompletionEvidence"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:PutObject",
    ]

    resources = [
      local.epss_history_completion_object_arn,
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
      "${local.epss_history_transformer_log_group_arn}:*",
    ]
  }

  statement {
    sid    = "WriteXRayTelemetry"
    effect = "Allow"

    actions = [
      "xray:PutTelemetryRecords",
      "xray:PutTraceSegments",
    ]

    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "epss_history_transformer_runtime" {
  name = "OpsLensEpssHistoryTransformerRuntimeAccess"
  role = aws_iam_role.epss_history_transformer.id

  policy = data.aws_iam_policy_document.epss_history_transformer_runtime.json
}

output "epss_history_transformer_execution_role_arn" {
  description = "ARN of the historical EPSS transformer Lambda execution role."
  value       = aws_iam_role.epss_history_transformer.arn
}
