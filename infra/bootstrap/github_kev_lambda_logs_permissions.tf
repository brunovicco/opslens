locals {
  dev_kev_lambda_log_group_name = "/aws/lambda/opslens-dev-kev-ingestion"

  dev_kev_lambda_log_group_arn = (
    "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:${local.dev_kev_lambda_log_group_name}"
  )

  dev_kev_lambda_log_group_iam_arn = (
    "${local.dev_kev_lambda_log_group_arn}:*"
  )
}

data "aws_iam_policy_document" "github_actions_kev_lambda_logs" {
  statement {
    sid    = "CreateKevLambdaLogGroup"
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:TagLogGroup",
    ]

    resources = [
      local.dev_kev_lambda_log_group_iam_arn,
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
      values   = ["kev-ingestion-observability"]
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
    sid    = "ManageKevLambdaLogGroup"
    effect = "Allow"

    actions = [
      "logs:DeleteLogGroup",
      "logs:PutRetentionPolicy",
      "logs:DeleteRetentionPolicy",
    ]

    resources = [
      local.dev_kev_lambda_log_group_iam_arn,
    ]
  }

  statement {
    sid    = "TagKevLambdaLogGroup"
    effect = "Allow"

    actions = [
      "logs:TagResource",
      "logs:UntagResource",
      "logs:ListTagsForResource",
    ]

    resources = [
      local.dev_kev_lambda_log_group_arn,
    ]
  }
}

resource "aws_iam_policy" "github_actions_kev_lambda_logs" {
  name = "OpsLensKevLambdaLogsDevAccess"

  description = "Allow OpsLens GitHub deployment automation to manage the KEV Lambda log group."

  policy = data.aws_iam_policy_document.github_actions_kev_lambda_logs.json
}

resource "aws_iam_role_policy_attachment" "github_actions_kev_lambda_logs" {
  role = aws_iam_role.github_actions_deploy.name

  policy_arn = aws_iam_policy.github_actions_kev_lambda_logs.arn
}
