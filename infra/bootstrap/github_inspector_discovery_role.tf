data "aws_iam_policy_document" "github_actions_inspector_discovery_assume_role" {
  # checkov:skip=CKV_AWS_358:GitHub immutable OIDC subject uses owner/repository IDs; Checkov does not yet recognize the official immutable sub format.
  statement {
    sid     = "AllowOpsLensMainBranchInspectorDiscovery"
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

resource "aws_iam_role" "github_actions_inspector_discovery" {
  name                 = "OpsLensInspectorDiscoveryRole"
  description          = "Temporary read-only GitHub Actions role for one bounded Amazon Inspector discovery experiment."
  assume_role_policy   = data.aws_iam_policy_document.github_actions_inspector_discovery_assume_role.json
  max_session_duration = 3600

  tags = {
    Purpose = "inspector-discovery-read-only-experiment"
  }
}

data "aws_iam_policy_document" "github_actions_inspector_discovery" {
  statement {
    sid    = "ReadInspectorDiscoveryEvidence"
    effect = "Allow"

    actions = [
      "inspector2:ListCoverage",
      "inspector2:ListFindings",
    ]

    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestedRegion"
      values   = ["us-east-1"]
    }
  }
}

resource "aws_iam_role_policy" "github_actions_inspector_discovery" {
  name = "OpsLensInspectorDiscoveryReadOnly"
  role = aws_iam_role.github_actions_inspector_discovery.id

  policy = data.aws_iam_policy_document.github_actions_inspector_discovery.json
}
