locals {
  dev_epss_history_coordinator_role_name = "OpsLensEpssHistoryCoordinatorRole"
  dev_epss_history_transformer_role_name = "OpsLensEpssHistoryTransformerLambdaRole"

  dev_epss_history_coordinator_role_arn = (
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${local.dev_epss_history_coordinator_role_name}"
  )

  dev_epss_history_transformer_role_arn = (
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${local.dev_epss_history_transformer_role_name}"
  )

  dev_epss_history_role_arns = [
    local.dev_epss_history_coordinator_role_arn,
    local.dev_epss_history_transformer_role_arn,
  ]

  dev_epss_history_transformer_function_name = "opslens-dev-epss-history-transformer"
  dev_epss_history_transformer_function_arn = (
    "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${local.dev_epss_history_transformer_function_name}"
  )

  dev_epss_history_transformer_log_group_name = (
    "/aws/lambda/${local.dev_epss_history_transformer_function_name}"
  )

  dev_epss_history_transformer_log_group_arn = (
    "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:${local.dev_epss_history_transformer_log_group_name}"
  )

  dev_epss_history_transformer_log_group_iam_arn = (
    "${local.dev_epss_history_transformer_log_group_arn}:*"
  )

  dev_nvd_incremental_function_arn = (
    "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:opslens-dev-nvd-incremental"
  )
}

data "aws_iam_policy_document" "github_actions_epss_history_deploy" {
  statement {
    sid     = "CreateEpssHistoryCoordinatorRole"
    effect  = "Allow"
    actions = ["iam:CreateRole"]

    resources = [
      local.dev_epss_history_coordinator_role_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Purpose"
      values   = ["epss-history-canary-coordinator"]
    }
  }

  statement {
    sid     = "CreateEpssHistoryTransformerRole"
    effect  = "Allow"
    actions = ["iam:CreateRole"]

    resources = [
      local.dev_epss_history_transformer_role_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Purpose"
      values   = ["epss-history-transformer-runtime"]
    }
  }

  statement {
    sid     = "TagEpssHistoryCoordinatorRoleOnCreate"
    effect  = "Allow"
    actions = ["iam:TagRole"]

    resources = [
      local.dev_epss_history_coordinator_role_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Purpose"
      values   = ["epss-history-canary-coordinator"]
    }
  }

  statement {
    sid     = "TagEpssHistoryTransformerRoleOnCreate"
    effect  = "Allow"
    actions = ["iam:TagRole"]

    resources = [
      local.dev_epss_history_transformer_role_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Purpose"
      values   = ["epss-history-transformer-runtime"]
    }
  }

  statement {
    sid    = "ReadEpssHistoryRoles"
    effect = "Allow"

    actions = [
      "iam:GetRole",
      "iam:GetRolePolicy",
      "iam:ListAttachedRolePolicies",
      "iam:ListInstanceProfilesForRole",
      "iam:ListRolePolicies",
      "iam:ListRoleTags",
    ]

    resources = local.dev_epss_history_role_arns
  }

  statement {
    sid     = "CreateEpssHistoryRoleInlinePolicies"
    effect  = "Allow"
    actions = ["iam:PutRolePolicy"]

    resources = local.dev_epss_history_role_arns
  }

  statement {
    sid     = "CreateEpssHistoryTransformerLogGroup"
    effect  = "Allow"
    actions = ["logs:CreateLogGroup"]

    resources = [
      local.dev_epss_history_transformer_log_group_iam_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Purpose"
      values   = ["epss-history-transformer-observability"]
    }
  }

  statement {
    sid    = "ConfigureEpssHistoryTransformerLogGroup"
    effect = "Allow"

    actions = [
      "logs:PutRetentionPolicy",
    ]

    resources = [
      local.dev_epss_history_transformer_log_group_iam_arn,
    ]
  }

  statement {
    sid     = "ReadEpssHistoryTransformerLogGroupTags"
    effect  = "Allow"
    actions = ["logs:ListTagsForResource"]

    resources = [
      local.dev_epss_history_transformer_log_group_arn,
    ]
  }

  statement {
    sid    = "TagEpssHistoryTransformerLogGroupOnCreate"
    effect = "Allow"
    actions = [
      "logs:TagLogGroup",
      "logs:TagResource",
    ]

    resources = [
      local.dev_epss_history_transformer_log_group_arn,
    ]
  }

  statement {
    sid     = "CreateEpssHistoryTransformerFunction"
    effect  = "Allow"
    actions = ["lambda:CreateFunction"]

    resources = [
      local.dev_epss_history_transformer_function_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Purpose"
      values   = ["epss-history-transformer"]
    }
  }

  statement {
    sid    = "ReadEpssHistoryTransformerFunction"
    effect = "Allow"

    actions = [
      "lambda:GetFunction",
      "lambda:GetFunctionCodeSigningConfig",
      "lambda:GetFunctionConcurrency",
      "lambda:GetFunctionConfiguration",
      "lambda:GetFunctionRecursionConfig",
      "lambda:GetRuntimeManagementConfig",
      "lambda:ListTags",
      "lambda:ListVersionsByFunction",
    ]

    resources = [
      local.dev_epss_history_transformer_function_arn,
    ]
  }

  statement {
    sid     = "PassEpssHistoryTransformerRole"
    effect  = "Allow"
    actions = ["iam:PassRole"]

    resources = [
      local.dev_epss_history_transformer_role_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["lambda.amazonaws.com"]
    }
  }

  statement {
    sid     = "UpdateNvdIncrementalFunctionCode"
    effect  = "Allow"
    actions = ["lambda:UpdateFunctionCode"]

    resources = [
      local.dev_nvd_incremental_function_arn,
    ]
  }
}

resource "aws_iam_policy" "github_actions_epss_history_deploy" {
  name        = "OpsLensEpssHistoryDeployDevAccess"
  description = "Allow GitHub Actions to create the bounded EPSS history runtime in dev."

  policy = data.aws_iam_policy_document.github_actions_epss_history_deploy.json
}

resource "aws_iam_role_policy_attachment" "github_actions_epss_history_deploy" {
  role       = aws_iam_role.github_actions_deploy.name
  policy_arn = aws_iam_policy.github_actions_epss_history_deploy.arn
}
