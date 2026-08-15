locals {
  epss_lambda_function_name       = "opslens-dev-epss-ingestion"
  epss_lambda_execution_role_name = "OpsLensEpssIngestionLambdaRole"

  epss_lambda_log_group_name = "/aws/lambda/${local.epss_lambda_function_name}"

  epss_lambda_log_group_arn = (
    "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:${local.epss_lambda_log_group_name}"
  )

  epss_bronze_object_arn = "${aws_s3_bucket.data.arn}/bronze/epss/*"
}

data "aws_iam_policy_document" "epss_lambda_assume_role" {
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

resource "aws_iam_role" "epss_ingestion_lambda" {
  name        = local.epss_lambda_execution_role_name
  description = "Execution role for the OpsLens EPSS ingestion Lambda."

  assume_role_policy = data.aws_iam_policy_document.epss_lambda_assume_role.json

  tags = {
    Purpose = "epss-ingestion-runtime"
  }
}

data "aws_iam_policy_document" "epss_lambda_runtime" {
  statement {
    sid    = "WriteEpssBronzeSnapshots"
    effect = "Allow"

    actions = [
      "s3:PutObject",
    ]

    resources = [
      local.epss_bronze_object_arn,
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
      "${local.epss_lambda_log_group_arn}:*",
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

resource "aws_iam_role_policy" "epss_lambda_runtime" {
  name = "OpsLensEpssIngestionRuntimeAccess"
  role = aws_iam_role.epss_ingestion_lambda.id

  policy = data.aws_iam_policy_document.epss_lambda_runtime.json
}

output "epss_lambda_execution_role_arn" {
  description = "ARN of the EPSS ingestion Lambda execution role."
  value       = aws_iam_role.epss_ingestion_lambda.arn
}
