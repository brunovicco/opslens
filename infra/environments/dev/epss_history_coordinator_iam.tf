data "aws_iam_openid_connect_provider" "epss_history_github_actions" {
  arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"
}

locals {
  epss_history_coordinator_role_name = "OpsLensEpssHistoryCoordinatorRole"
}

data "aws_iam_policy_document" "epss_history_coordinator_assume_role" {
  statement {
    sid     = "AllowGitHubActionsMain"
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.epss_history_github_actions.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:brunovicco/opslens:ref:refs/heads/main"]
    }
  }
}

resource "aws_iam_role" "epss_history_coordinator" {
  name        = local.epss_history_coordinator_role_name
  description = "Bounded GitHub Actions coordinator role for the seven-snapshot EPSS history canary."

  assume_role_policy = data.aws_iam_policy_document.epss_history_coordinator_assume_role.json

  tags = {
    Purpose = "epss-history-canary-coordinator"
  }
}

data "aws_iam_policy_document" "epss_history_coordinator_runtime" {
  statement {
    sid    = "DiscoverForwardEpssBoundary"
    effect = "Allow"

    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.data.arn]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["bronze/epss/*"]
    }
  }

  statement {
    sid    = "CreateAndVerifyHistoricalBronze"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:PutObject",
    ]

    resources = [
      local.epss_history_bronze_object_arn,
    ]
  }

  statement {
    sid    = "InvokeHistoricalTransformerSynchronously"
    effect = "Allow"

    actions = [
      "lambda:InvokeFunction",
    ]

    resources = [
      aws_lambda_function.epss_history_transformer.arn,
    ]
  }
}

resource "aws_iam_role_policy" "epss_history_coordinator_runtime" {
  name = "OpsLensEpssHistoryCoordinatorRuntimeAccess"
  role = aws_iam_role.epss_history_coordinator.id

  policy = data.aws_iam_policy_document.epss_history_coordinator_runtime.json
}

output "epss_history_coordinator_role_arn" {
  description = "ARN of the bounded EPSS history canary coordinator role."
  value       = aws_iam_role.epss_history_coordinator.arn
}
