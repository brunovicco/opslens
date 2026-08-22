locals {
  nvd_silver_lambda_function_name       = "opslens-dev-nvd-silver"
  nvd_silver_lambda_execution_role_name = "OpsLensNvdSilverLambdaRole"

  nvd_silver_lambda_log_group_name = (
    "/aws/lambda/${local.nvd_silver_lambda_function_name}"
  )

  nvd_silver_lambda_log_group_arn = (
    "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:${local.nvd_silver_lambda_log_group_name}"
  )

  nvd_silver_bootstrap_bronze_object_arn = (
    "${aws_s3_bucket.data.arn}/bronze/nvd/cve/bootstrap/*"
  )

  nvd_silver_incremental_bronze_object_arn = (
    "${aws_s3_bucket.data.arn}/bronze/nvd/cve/updates/*"
  )

  nvd_silver_object_arn = (
    "${aws_s3_bucket.data.arn}/silver/nvd/cve/*"
  )
}

data "aws_iam_policy_document" "nvd_silver_lambda_assume_role" {
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

resource "aws_iam_role" "nvd_silver_lambda" {
  name        = local.nvd_silver_lambda_execution_role_name
  description = "Execution role for the OpsLens NVD Bronze-to-Silver transformation Lambda."

  assume_role_policy = (
    data.aws_iam_policy_document.nvd_silver_lambda_assume_role.json
  )

  tags = {
    Purpose = "nvd-silver-runtime"
  }
}

data "aws_iam_policy_document" "nvd_silver_lambda_runtime" {
  statement {
    sid    = "ReadExactNvdBronzeVersions"
    effect = "Allow"

    actions = [
      "s3:GetObjectVersion",
    ]

    resources = [
      local.nvd_silver_bootstrap_bronze_object_arn,
      local.nvd_silver_incremental_bronze_object_arn,
    ]
  }

  statement {
    sid    = "WriteNvdSilverArtifacts"
    effect = "Allow"

    actions = [
      "s3:PutObject",
    ]

    resources = [
      local.nvd_silver_object_arn,
    ]
  }

  statement {
    sid    = "ReadCurrentNvdSilverObjects"
    effect = "Allow"

    actions = [
      "s3:GetObject",
    ]

    resources = [
      local.nvd_silver_object_arn,
    ]
  }

  statement {
    sid    = "ReadExactNvdSilverVersions"
    effect = "Allow"

    actions = [
      "s3:GetObjectVersion",
    ]

    resources = [
      local.nvd_silver_object_arn,
    ]
  }

  statement {
    sid    = "SendNvdSilverFailureRecords"
    effect = "Allow"

    actions = [
      "sqs:SendMessage",
    ]

    resources = [
      aws_sqs_queue.nvd_silver_failures.arn,
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
      "${local.nvd_silver_lambda_log_group_arn}:*",
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

resource "aws_iam_role_policy" "nvd_silver_lambda_runtime" {
  name = "OpsLensNvdSilverRuntimeAccess"
  role = aws_iam_role.nvd_silver_lambda.id

  policy = (
    data.aws_iam_policy_document.nvd_silver_lambda_runtime.json
  )
}

output "nvd_silver_lambda_execution_role_arn" {
  description = "ARN of the NVD Silver Lambda execution role."
  value       = aws_iam_role.nvd_silver_lambda.arn
}
