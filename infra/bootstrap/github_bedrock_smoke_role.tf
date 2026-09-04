locals {
  bedrock_smoke_role_name = "OpsLensBedrockSmokeRole"
  bedrock_smoke_model_id  = "anthropic.claude-haiku-4-5-20251001-v1:0"
  bedrock_smoke_model_arn = "arn:aws:bedrock:us-east-1::foundation-model/${local.bedrock_smoke_model_id}"
}

data "aws_iam_policy_document" "github_bedrock_smoke_assume_role" {
  statement {
    sid     = "AllowPhase6Gate64Branch"
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
        "repo:brunovicco@38844444/opslens@1333092779:ref:refs/heads/feat/phase6-gate-6-4-bedrock-smoke",
      ]
    }
  }
}

resource "aws_iam_role" "github_bedrock_smoke" {
  name                 = local.bedrock_smoke_role_name
  description          = "One-branch role for the bounded OpsLens Phase 6 Gate 6.4 Bedrock smoke."
  assume_role_policy   = data.aws_iam_policy_document.github_bedrock_smoke_assume_role.json
  max_session_duration = 3600

  tags = {
    Purpose = "phase6-gate-6-4-bedrock-smoke"
  }
}

data "aws_iam_policy_document" "github_bedrock_smoke" {
  statement {
    sid     = "InvokeFrozenPlannerModel"
    effect  = "Allow"
    actions = ["bedrock:InvokeModel"]
    resources = [
      local.bedrock_smoke_model_arn,
    ]
  }
}

resource "aws_iam_role_policy" "github_bedrock_smoke" {
  name   = "OpsLensBedrockSmokeInvokeModel"
  role   = aws_iam_role.github_bedrock_smoke.id
  policy = data.aws_iam_policy_document.github_bedrock_smoke.json
}

output "github_bedrock_smoke_role_arn" {
  description = "Dedicated OIDC role for the Phase 6 Gate 6.4 Bedrock smoke."
  value       = aws_iam_role.github_bedrock_smoke.arn
}
