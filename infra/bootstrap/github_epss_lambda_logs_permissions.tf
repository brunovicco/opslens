locals {
  dev_epss_lambda_log_group_name = "/aws/lambda/opslens-dev-epss-ingestion"

  # CloudWatch Logs uses two ARN forms:
  # - with :* for most log-group management actions;
  # - without :* for TagResource, UntagResource, and ListTagsForResource.
  dev_epss_lambda_log_group_arn = (
    "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:${local.dev_epss_lambda_log_group_name}"
  )

  dev_epss_lambda_log_group_iam_arn = (
    "${local.dev_epss_lambda_log_group_arn}:*"
  )
}

data "aws_iam_policy_document" "github_actions_epss_lambda_logs" {
  statement {
    sid    = "ManageEpssLambdaLogGroup"
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:DeleteLogGroup",
      "logs:PutRetentionPolicy",
      "logs:DeleteRetentionPolicy",
    ]

    resources = [
      local.dev_epss_lambda_log_group_iam_arn,
    ]
  }

  statement {
    sid     = "TagOnCreateEpssLambdaLogGroup"
    effect  = "Allow"
    actions = ["logs:TagResource"]

    # The resource does not exist yet during CreateLogGroup, so create-time
    # tagging is restricted by the exact Terraform tags requested.
    resources = ["*"]

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
    sid    = "TagEpssLambdaLogGroup"
    effect = "Allow"

    actions = [
      "logs:TagResource",
      "logs:UntagResource",
      "logs:ListTagsForResource",
    ]

    resources = [
      local.dev_epss_lambda_log_group_arn,
    ]
  }
}

resource "aws_iam_role_policy" "github_actions_epss_lambda_logs" {
  name = "OpsLensEpssLambdaLogsDevAccess"
  role = aws_iam_role.github_actions_deploy.id

  policy = data.aws_iam_policy_document.github_actions_epss_lambda_logs.json
}
