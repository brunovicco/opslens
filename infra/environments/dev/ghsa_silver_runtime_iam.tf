locals {
  ghsa_silver_lambda_function_name       = "opslens-dev-ghsa-silver"
  ghsa_silver_lambda_execution_role_name = "OpsLensGhsaSilverLambdaRole"

  ghsa_silver_lambda_log_group_name = (
    "/aws/lambda/${local.ghsa_silver_lambda_function_name}"
  )

  ghsa_silver_lambda_log_group_arn = (
    "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:${local.ghsa_silver_lambda_log_group_name}"
  )

  ghsa_silver_bronze_object_arn = (
    "${aws_s3_bucket.data.arn}/bronze/ghsa/advisories/*"
  )

  ghsa_silver_advisory_versions_object_arn = (
    "${aws_s3_bucket.data.arn}/silver/ghsa/advisory_versions/*"
  )

  ghsa_silver_completions_object_arn = (
    "${aws_s3_bucket.data.arn}/silver/ghsa/completions/*"
  )
}

data "aws_iam_policy_document" "ghsa_silver_lambda_assume_role" {
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

resource "aws_iam_role" "ghsa_silver_lambda" {
  name = local.ghsa_silver_lambda_execution_role_name

  description = (
    "Execution role for the OpsLens GHSA Bronze-to-Silver transformation Lambda."
  )

  assume_role_policy = (
    data.aws_iam_policy_document.ghsa_silver_lambda_assume_role.json
  )

  tags = {
    Purpose = "ghsa-silver-runtime"
  }
}

data "aws_iam_policy_document" "ghsa_silver_lambda_runtime" {
  statement {
    sid    = "ReadExactGhsaBronzeVersions"
    effect = "Allow"

    actions = [
      "s3:GetObjectVersion",
    ]

    resources = [
      local.ghsa_silver_bronze_object_arn,
    ]
  }

  statement {
    sid    = "WriteGhsaSilverArtifacts"
    effect = "Allow"

    actions = [
      "s3:PutObject",
    ]

    resources = [
      local.ghsa_silver_advisory_versions_object_arn,
      local.ghsa_silver_completions_object_arn,
    ]
  }

  statement {
    sid    = "ReadCurrentGhsaSilverObjects"
    effect = "Allow"

    actions = [
      "s3:GetObject",
    ]

    resources = [
      local.ghsa_silver_advisory_versions_object_arn,
      local.ghsa_silver_completions_object_arn,
    ]
  }

  statement {
    sid    = "ReadExactGhsaSilverVersions"
    effect = "Allow"

    actions = [
      "s3:GetObjectVersion",
    ]

    resources = [
      local.ghsa_silver_advisory_versions_object_arn,
      local.ghsa_silver_completions_object_arn,
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
      "${local.ghsa_silver_lambda_log_group_arn}:*",
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

resource "aws_iam_role_policy" "ghsa_silver_lambda_runtime" {
  name = "OpsLensGhsaSilverRuntimeAccess"
  role = aws_iam_role.ghsa_silver_lambda.id

  policy = (
    data.aws_iam_policy_document.ghsa_silver_lambda_runtime.json
  )
}

output "ghsa_silver_lambda_execution_role_arn" {
  description = "ARN of the GHSA Silver Lambda execution role."
  value       = aws_iam_role.ghsa_silver_lambda.arn
}
