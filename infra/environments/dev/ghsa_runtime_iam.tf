locals {
  ghsa_bronze_lambda_function_name = "opslens-dev-ghsa-bronze"

  ghsa_bronze_lambda_execution_role_name = (
    "OpsLensGhsaBronzeLambdaRole"
  )

  ghsa_bronze_lambda_log_group_name = (
    "/aws/lambda/${local.ghsa_bronze_lambda_function_name}"
  )

  ghsa_bronze_lambda_log_group_arn = (
    "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:${local.ghsa_bronze_lambda_log_group_name}"
  )

  ghsa_bronze_object_arn = (
    "${aws_s3_bucket.data.arn}/bronze/ghsa/advisories/*"
  )
}

data "aws_iam_policy_document" "ghsa_bronze_lambda_assume_role" {
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

resource "aws_iam_role" "ghsa_bronze_lambda" {
  name = local.ghsa_bronze_lambda_execution_role_name

  description = (
    "Execution role for the OpsLens GHSA Bronze ingestion Lambda."
  )

  assume_role_policy = (
    data.aws_iam_policy_document.ghsa_bronze_lambda_assume_role.json
  )

  tags = {
    Purpose = "ghsa-bronze-runtime"
  }
}

data "aws_iam_policy_document" "ghsa_bronze_lambda_runtime" {
  statement {
    sid    = "ReadGhsaGitHubToken"
    effect = "Allow"

    actions = [
      "secretsmanager:GetSecretValue",
    ]

    resources = [
      aws_secretsmanager_secret.ghsa_github_token.arn,
    ]
  }

  statement {
    sid    = "WriteAndVerifyGhsaBronze"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
    ]

    resources = [
      local.ghsa_bronze_object_arn,
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
      "${local.ghsa_bronze_lambda_log_group_arn}:*",
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

resource "aws_iam_role_policy" "ghsa_bronze_lambda_runtime" {
  name = "OpsLensGhsaBronzeRuntimeAccess"
  role = aws_iam_role.ghsa_bronze_lambda.id

  policy = (
    data.aws_iam_policy_document.ghsa_bronze_lambda_runtime.json
  )
}

output "ghsa_bronze_lambda_execution_role_arn" {
  description = "ARN of the GHSA Bronze Lambda execution role."
  value       = aws_iam_role.ghsa_bronze_lambda.arn
}
