locals {
  dev_epss_lambda_log_group_name        = "/aws/lambda/opslens-dev-epss-ingestion"
  dev_epss_silver_lambda_log_group_name = "/aws/lambda/opslens-dev-epss-silver"

  # CloudWatch Logs uses two ARN forms:
  # - with :* for most log-group management actions;
  # - without :* for TagResource, UntagResource, and ListTagsForResource.
  dev_epss_lambda_log_group_arn = (
    "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:${local.dev_epss_lambda_log_group_name}"
  )

  dev_epss_silver_lambda_log_group_arn = (
    "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:${local.dev_epss_silver_lambda_log_group_name}"
  )

  dev_epss_lambda_log_group_iam_arn = (
    "${local.dev_epss_lambda_log_group_arn}:*"
  )

  dev_epss_silver_lambda_log_group_iam_arn = (
    "${local.dev_epss_silver_lambda_log_group_arn}:*"
  )

  dev_epss_lambda_log_group_arns = [
    local.dev_epss_lambda_log_group_arn,
    local.dev_epss_silver_lambda_log_group_arn,
  ]

  dev_epss_lambda_log_group_iam_arns = [
    local.dev_epss_lambda_log_group_iam_arn,
    local.dev_epss_silver_lambda_log_group_iam_arn,
  ]
}

data "aws_iam_policy_document" "github_actions_epss_lambda_logs" {
  statement {
    sid     = "CreateEpssLambdaLogGroup"
    effect  = "Allow"
    actions = ["logs:CreateLogGroup"]

    resources = [
      local.dev_epss_lambda_log_group_iam_arn,
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
      values   = ["epss-ingestion-observability"]
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
    sid     = "CreateEpssSilverLambdaLogGroup"
    effect  = "Allow"
    actions = ["logs:CreateLogGroup"]

    resources = [
      local.dev_epss_silver_lambda_log_group_iam_arn,
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
      values   = ["epss-silver-observability"]
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
    sid    = "ManageEpssLambdaLogGroups"
    effect = "Allow"

    actions = [
      "logs:DeleteLogGroup",
      "logs:PutRetentionPolicy",
      "logs:DeleteRetentionPolicy",
    ]

    resources = local.dev_epss_lambda_log_group_iam_arns
  }

  statement {
    sid    = "TagEpssLambdaLogGroups"
    effect = "Allow"

    actions = [
      "logs:TagResource",
      "logs:UntagResource",
      "logs:ListTagsForResource",
    ]

    resources = local.dev_epss_lambda_log_group_arns
  }
}

resource "aws_iam_role_policy" "github_actions_epss_lambda_logs" {
  name = "OpsLensEpssLambdaLogsDevAccess"
  role = aws_iam_role.github_actions_deploy.id

  policy = data.aws_iam_policy_document.github_actions_epss_lambda_logs.json
}
