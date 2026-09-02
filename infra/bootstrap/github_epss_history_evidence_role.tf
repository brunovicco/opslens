data "aws_iam_policy_document" "github_actions_epss_history_evidence_assume_role" {
  # checkov:skip=CKV_AWS_358:GitHub immutable OIDC subject uses owner/repository IDs; Checkov does not yet recognize the official immutable sub format.
  statement {
    sid     = "AllowOpsLensMainBranchEvidence"
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type = "Federated"
      identifiers = [
        aws_iam_openid_connect_provider.github_actions.arn,
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:brunovicco@38844444/opslens@1333092779:ref:refs/heads/main",
      ]
    }
  }
}

resource "aws_iam_role" "github_actions_epss_history_evidence" {
  name                 = "OpsLensEpssHistoryEvidenceRole"
  description          = "Read-only GitHub Actions role for EPSS historical backfill evidence verification."
  assume_role_policy   = data.aws_iam_policy_document.github_actions_epss_history_evidence_assume_role.json
  max_session_duration = 21600

  tags = {
    Purpose = "epss-history-evidence-read-only"
  }
}

data "aws_iam_policy_document" "github_actions_epss_history_evidence" {
  statement {
    sid    = "ListEpssEvidence"
    effect = "Allow"

    actions = [
      "s3:ListBucket",
      "s3:ListBucketVersions",
    ]

    resources = [
      local.dev_data_bucket_arn,
    ]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values = [
        "bronze/epss/*",
        "bronze/epss-history/*",
        "silver/epss/*",
        "silver/epss-history/completions/*",
      ]
    }
  }

  statement {
    sid    = "ReadEpssHistoricalEvidence"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion",
    ]

    resources = [
      "${local.dev_data_bucket_arn}/bronze/epss-history/*",
      "${local.dev_data_bucket_arn}/silver/epss/*",
      "${local.dev_data_bucket_arn}/silver/epss-history/completions/*",
    ]
  }
}

resource "aws_iam_role_policy" "github_actions_epss_history_evidence" {
  name = "OpsLensEpssHistoryEvidenceReadOnly"
  role = aws_iam_role.github_actions_epss_history_evidence.id

  policy = data.aws_iam_policy_document.github_actions_epss_history_evidence.json
}
