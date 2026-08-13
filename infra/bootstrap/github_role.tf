data "aws_iam_policy_document" "github_actions_assume_role" {
  statement {
    sid     = "AllowOpsLensMainBranch"
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

resource "aws_iam_role" "github_actions_deploy" {
  name                 = "OpsLensGitHubDeployRole"
  description          = "Deployment role assumed by OpsLens GitHub Actions through OIDC."
  assume_role_policy   = data.aws_iam_policy_document.github_actions_assume_role.json
  max_session_duration = 3600

  tags = {
    Purpose = "github-actions-deployment"
  }
}
