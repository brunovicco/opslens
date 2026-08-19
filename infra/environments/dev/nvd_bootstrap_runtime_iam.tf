locals {
  nvd_bootstrap_lambda_function_name       = "opslens-dev-nvd-bootstrap-ingestion"
  nvd_bootstrap_lambda_execution_role_name = "OpsLensNvdBootstrapIngestionLambdaRole"

  nvd_bootstrap_lambda_log_group_name = "/aws/lambda/${local.nvd_bootstrap_lambda_function_name}"

  nvd_bootstrap_lambda_log_group_arn = (
    "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:${local.nvd_bootstrap_lambda_log_group_name}"
  )

  nvd_bootstrap_bronze_object_arn = (
    "${aws_s3_bucket.data.arn}/bronze/nvd/cve/bootstrap/*"
  )
}

data "aws_iam_policy_document" "nvd_bootstrap_lambda_assume_role" {
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

resource "aws_iam_role" "nvd_bootstrap_ingestion_lambda" {
  name        = local.nvd_bootstrap_lambda_execution_role_name
  description = "Execution role for the OpsLens NVD Bootstrap ingestion Lambda."

  assume_role_policy = data.aws_iam_policy_document.nvd_bootstrap_lambda_assume_role.json

  tags = {
    Purpose = "nvd-bootstrap-ingestion-runtime"
  }
}

data "aws_iam_policy_document" "nvd_bootstrap_lambda_runtime" {
  statement {
    sid    = "WriteAndVerifyNvdBootstrapBronze"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
    ]

    resources = [
      local.nvd_bootstrap_bronze_object_arn,
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
      "${local.nvd_bootstrap_lambda_log_group_arn}:*",
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

resource "aws_iam_role_policy" "nvd_bootstrap_lambda_runtime" {
  name = "OpsLensNvdBootstrapIngestionRuntimeAccess"
  role = aws_iam_role.nvd_bootstrap_ingestion_lambda.id

  policy = data.aws_iam_policy_document.nvd_bootstrap_lambda_runtime.json
}

output "nvd_bootstrap_lambda_execution_role_arn" {
  description = "ARN of the NVD Bootstrap ingestion Lambda execution role."
  value       = aws_iam_role.nvd_bootstrap_ingestion_lambda.arn
}
