locals {
  epss_silver_lambda_function_name       = "opslens-dev-epss-silver"
  epss_silver_lambda_execution_role_name = "OpsLensEpssSilverLambdaRole"

  epss_silver_lambda_log_group_name = "/aws/lambda/${local.epss_silver_lambda_function_name}"

  epss_silver_lambda_log_group_arn = (
    "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:${local.epss_silver_lambda_log_group_name}"
  )

  epss_silver_bronze_object_arn = "${aws_s3_bucket.data.arn}/bronze/epss/*"
  epss_silver_object_arn        = "${aws_s3_bucket.data.arn}/silver/epss/*"
}

data "aws_iam_policy_document" "epss_silver_lambda_assume_role" {
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

resource "aws_iam_role" "epss_silver_lambda" {
  name        = local.epss_silver_lambda_execution_role_name
  description = "Execution role for the OpsLens EPSS Bronze-to-Silver transformation Lambda."

  assume_role_policy = data.aws_iam_policy_document.epss_silver_lambda_assume_role.json

  tags = {
    Purpose = "epss-silver-runtime"
  }
}

data "aws_iam_policy_document" "epss_silver_lambda_runtime" {
  statement {
    sid    = "ReadEpssBronzeSnapshots"
    effect = "Allow"

    actions = [
      "s3:GetObject",
    ]

    resources = [
      local.epss_silver_bronze_object_arn,
    ]
  }

  statement {
    sid    = "SendSilverFailureRecords"
    effect = "Allow"

    actions = [
      "sqs:SendMessage",
    ]

    resources = [
      aws_sqs_queue.epss_silver_failures.arn,
    ]
  }

  statement {
    sid    = "WriteEpssSilverSnapshots"
    effect = "Allow"

    actions = [
      "s3:PutObject",
    ]

    resources = [
      local.epss_silver_object_arn,
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
      "${local.epss_silver_lambda_log_group_arn}:*",
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

resource "aws_iam_role_policy" "epss_silver_lambda_runtime" {
  name = "OpsLensEpssSilverRuntimeAccess"
  role = aws_iam_role.epss_silver_lambda.id

  policy = data.aws_iam_policy_document.epss_silver_lambda_runtime.json
}

output "epss_silver_lambda_execution_role_arn" {
  description = "ARN of the EPSS Silver transformation Lambda execution role."
  value       = aws_iam_role.epss_silver_lambda.arn
}
