locals {
  dev_agentcore_replay_runtime_name = "opslens_dev_bounded_runtime"

  dev_agentcore_replay_runtime_arn = (
    "arn:aws:bedrock-agentcore:${var.aws_region}:${data.aws_caller_identity.current.account_id}:runtime/${local.dev_agentcore_replay_runtime_name}-*"
  )

  dev_agentcore_replay_runtime_endpoint_arn = (
    "${local.dev_agentcore_replay_runtime_arn}/runtime-endpoint/*"
  )
}

data "aws_iam_policy_document" "github_actions_agentcore_replay_assume_role" {
  # checkov:skip=CKV_AWS_358:GitHub immutable OIDC subject uses owner/repository IDs; Checkov does not yet recognize the official immutable sub format.
  statement {
    sid     = "AllowOpsLensMainBranchAgentCoreReplay"
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

resource "aws_iam_role" "github_actions_agentcore_replay" {
  name                 = "OpsLensAgentCoreReplayRole"
  description          = "Invocation-only GitHub Actions role for the bounded Phase 14 AgentCore replay."
  assume_role_policy   = data.aws_iam_policy_document.github_actions_agentcore_replay_assume_role.json
  max_session_duration = 3600

  tags = {
    Purpose = "agentcore-runtime-replay-invocation"
  }
}

data "aws_iam_policy_document" "github_actions_agentcore_replay" {
  statement {
    sid     = "InvokeOnlyBoundedAgentCoreRuntime"
    effect  = "Allow"
    actions = ["bedrock-agentcore:InvokeAgentRuntime"]

    resources = [
      local.dev_agentcore_replay_runtime_arn,
      local.dev_agentcore_replay_runtime_endpoint_arn,
    ]
  }
}

resource "aws_iam_role_policy" "github_actions_agentcore_replay" {
  name = "OpsLensAgentCoreReplayInvokeOnly"
  role = aws_iam_role.github_actions_agentcore_replay.id

  policy = data.aws_iam_policy_document.github_actions_agentcore_replay.json
}
