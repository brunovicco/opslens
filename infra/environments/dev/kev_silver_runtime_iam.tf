locals {
  kev_silver_lambda_function_name       = "opslens-dev-kev-silver"
  kev_silver_lambda_execution_role_name = "OpsLensKevSilverLambdaRole"

  kev_silver_lambda_log_group_name = (
    "/aws/lambda/${local.kev_silver_lambda_function_name}"
  )

  kev_silver_lambda_log_group_arn = (
    "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:${local.kev_silver_lambda_log_group_name}"
  )

  kev_silver_bronze_object_arn = (
    "${aws_s3_bucket.data.arn}/bronze/kev/*"
  )

  kev_silver_object_arn = (
    "${aws_s3_bucket.data.arn}/silver/kev/*"
  )
}

data "aws_iam_policy_document" "kev_silver_lambda_assume_role" {
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

resource "aws_iam_role" "kev_silver_lambda" {
  name        = local.kev_silver_lambda_execution_role_name
  description = "Execution role for the OpsLens CISA KEV Bronze-to-Silver transformation Lambda."

  assume_role_policy = (
    data.aws_iam_policy_document.kev_silver_lambda_assume_role.json
  )

  tags = {
    Purpose = "kev-silver-runtime"
  }
}

data "aws_iam_policy_document" "kev_silver_lambda_runtime" {
  statement {
    sid    = "ReadExactKevBronzeVersions"
    effect = "Allow"

    actions = [
      "s3:GetObjectVersion",
    ]

    resources = [
      local.kev_silver_bronze_object_arn,
    ]
  }

  statement {
    sid    = "WriteKevSilverSnapshots"
    effect = "Allow"

    actions = [
      "s3:PutObject",
    ]

    resources = [
      local.kev_silver_object_arn,
    ]
  }

  statement {
    sid    = "SendKevSilverFailureRecords"
    effect = "Allow"

    actions = [
      "sqs:SendMessage",
    ]

    resources = [
      aws_sqs_queue.kev_silver_failures.arn,
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
      "${local.kev_silver_lambda_log_group_arn}:*",
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

resource "aws_iam_role_policy" "kev_silver_lambda_runtime" {
  name = "OpsLensKevSilverRuntimeAccess"
  role = aws_iam_role.kev_silver_lambda.id

  policy = data.aws_iam_policy_document.kev_silver_lambda_runtime.json
}
