locals {
  dev_kev_lambda_function_name = "opslens-dev-kev-ingestion"

  dev_kev_lambda_function_arn = (
    "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${local.dev_kev_lambda_function_name}"
  )
}

data "aws_iam_policy_document" "github_actions_kev_lambda" {
  statement {
    sid    = "CreateKevLambdaFunction"
    effect = "Allow"

    actions = [
      "lambda:CreateFunction",
    ]

    resources = [
      local.dev_kev_lambda_function_arn,
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
      values   = ["kev-ingestion"]
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
    sid    = "ManageKevLambdaFunction"
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
      local.dev_kev_lambda_function_arn,
    ]
  }

  statement {
    sid     = "PassKevLambdaExecutionRole"
    effect  = "Allow"
    actions = ["iam:PassRole"]

    resources = [
      local.dev_kev_lambda_execution_role_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_policy" "github_actions_kev_lambda" {
  name = "OpsLensKevLambdaDevAccess"

  description = "Allow OpsLens GitHub deployment automation to manage the KEV ingestion Lambda."

  policy = data.aws_iam_policy_document.github_actions_kev_lambda.json
}

resource "aws_iam_role_policy_attachment" "github_actions_kev_lambda" {
  role = aws_iam_role.github_actions_deploy.name

  policy_arn = aws_iam_policy.github_actions_kev_lambda.arn
}
