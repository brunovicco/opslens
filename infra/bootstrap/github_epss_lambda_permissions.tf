locals {
  dev_epss_lambda_function_name = "opslens-dev-epss-ingestion"

  dev_epss_lambda_function_arn = (
    "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${local.dev_epss_lambda_function_name}"
  )
}

data "aws_iam_policy_document" "github_actions_epss_lambda" {
  statement {
    sid    = "CreateEpssLambdaFunction"
    effect = "Allow"

    actions = [
      "lambda:CreateFunction",
    ]

    resources = [
      local.dev_epss_lambda_function_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Project"
      values   = ["opslens"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Environment"
      values   = ["dev"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/ManagedBy"
      values   = ["terraform"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Repository"
      values   = ["brunovicco/opslens"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Purpose"
      values   = ["epss-ingestion"]
    }

    condition {
      test     = "ForAllValues:StringEquals"
      variable = "aws:TagKeys"

      values = [
        "Project",
        "Environment",
        "ManagedBy",
        "Repository",
        "Purpose",
      ]
    }
  }

  statement {
    sid    = "ManageEpssLambdaFunction"
    effect = "Allow"

    actions = [
      "lambda:DeleteFunction",
      "lambda:GetFunction",
      "lambda:GetFunctionCodeSigningConfig",
      "lambda:GetFunctionConcurrency",
      "lambda:GetFunctionConfiguration",
      "lambda:GetFunctionRecursionConfig",
      "lambda:GetRuntimeManagementConfig",
      "lambda:ListTags",
      "lambda:ListVersionsByFunction",
      "lambda:TagResource",
      "lambda:UntagResource",
      "lambda:UpdateFunctionCode",
      "lambda:UpdateFunctionConfiguration",
    ]

    resources = [
      local.dev_epss_lambda_function_arn,
    ]
  }

  statement {
    sid    = "PassEpssLambdaExecutionRole"
    effect = "Allow"

    actions = [
      "iam:PassRole",
    ]

    resources = [
      local.dev_epss_lambda_execution_role_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "github_actions_epss_lambda" {
  name = "OpsLensEpssLambdaDevAccess"
  role = aws_iam_role.github_actions_deploy.id

  policy = data.aws_iam_policy_document.github_actions_epss_lambda.json
}
