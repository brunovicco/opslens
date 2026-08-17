locals {
  kev_lambda_function_name       = "opslens-dev-kev-ingestion"
  kev_lambda_execution_role_name = "OpsLensKevIngestionLambdaRole"

  kev_lambda_log_group_name = "/aws/lambda/${local.kev_lambda_function_name}"

  kev_lambda_log_group_arn = (
    "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:${local.kev_lambda_log_group_name}"
  )

  kev_bronze_object_arn = "${aws_s3_bucket.data.arn}/bronze/kev/*"
}

data "aws_iam_policy_document" "kev_lambda_assume_role" {
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

resource "aws_iam_role" "kev_ingestion_lambda" {
  name        = local.kev_lambda_execution_role_name
  description = "Execution role for the OpsLens CISA KEV ingestion Lambda."

  assume_role_policy = data.aws_iam_policy_document.kev_lambda_assume_role.json

  tags = {
    Purpose = "kev-ingestion-runtime"
  }
}

data "aws_iam_policy_document" "kev_lambda_runtime" {
  statement {
    sid    = "WriteKevBronzeSnapshots"
    effect = "Allow"

    actions = [
      "s3:PutObject",
    ]

    resources = [
      local.kev_bronze_object_arn,
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
      "${local.kev_lambda_log_group_arn}:*",
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

resource "aws_iam_role_policy" "kev_lambda_runtime" {
  name = "OpsLensKevIngestionRuntimeAccess"
  role = aws_iam_role.kev_ingestion_lambda.id

  policy = data.aws_iam_policy_document.kev_lambda_runtime.json
}

output "kev_lambda_execution_role_arn" {
  description = "ARN of the CISA KEV ingestion Lambda execution role."
  value       = aws_iam_role.kev_ingestion_lambda.arn
}
