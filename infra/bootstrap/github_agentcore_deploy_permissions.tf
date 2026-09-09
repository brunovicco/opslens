locals {
  dev_agentcore_runtime_name                = "opslens_dev_bounded_runtime"
  dev_agentcore_runtime_execution_role_name = "OpsLensAgentCoreRuntimeExecutionRole"
  dev_agentcore_runtime_purpose             = "bounded-agentcore-runtime-experiment"

  dev_agentcore_runtime_execution_role_arn = (
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${local.dev_agentcore_runtime_execution_role_name}"
  )

  dev_agentcore_runtime_precreation_arn = (
    "arn:aws:bedrock-agentcore:${var.aws_region}:${data.aws_caller_identity.current.account_id}:runtime/*"
  )

  dev_agentcore_runtime_arn = (
    "arn:aws:bedrock-agentcore:${var.aws_region}:${data.aws_caller_identity.current.account_id}:runtime/${local.dev_agentcore_runtime_name}-*"
  )

  dev_agentcore_runtime_endpoint_arn = (
    "${local.dev_agentcore_runtime_arn}/runtime-endpoint/*"
  )

  dev_agentcore_workload_identity_directory_arn = (
    "arn:aws:bedrock-agentcore:${var.aws_region}:${data.aws_caller_identity.current.account_id}:workload-identity-directory/default"
  )

  dev_agentcore_workload_identity_precreation_arn = (
    "${local.dev_agentcore_workload_identity_directory_arn}/workload-identity/*"
  )

  dev_agentcore_workload_identity_arn = (
    "${local.dev_agentcore_workload_identity_directory_arn}/workload-identity/${local.dev_agentcore_runtime_name}-*"
  )

  dev_agentcore_artifact_arn = (
    "${local.dev_artifacts_bucket_arn}/agentcore/runtime/*"
  )
}

data "aws_iam_policy_document" "github_actions_agentcore_deploy" {
  statement {
    sid    = "PublishAgentCoreRuntimeArtifact"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:PutObject",
    ]

    resources = [
      local.dev_agentcore_artifact_arn,
    ]
  }

  statement {
    sid     = "CreateAgentCoreRuntimeExecutionRole"
    effect  = "Allow"
    actions = ["iam:CreateRole"]

    resources = [
      local.dev_agentcore_runtime_execution_role_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Purpose"
      values   = ["bounded-agentcore-runtime-execution"]
    }
  }

  statement {
    sid     = "TagAgentCoreRuntimeExecutionRoleOnCreate"
    effect  = "Allow"
    actions = ["iam:TagRole"]

    resources = [
      local.dev_agentcore_runtime_execution_role_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Purpose"
      values   = ["bounded-agentcore-runtime-execution"]
    }
  }

  statement {
    sid    = "ManageAgentCoreRuntimeExecutionRole"
    effect = "Allow"

    actions = [
      "iam:DeleteRole",
      "iam:DeleteRolePolicy",
      "iam:GetRole",
      "iam:GetRolePolicy",
      "iam:ListAttachedRolePolicies",
      "iam:ListInstanceProfilesForRole",
      "iam:ListRolePolicies",
      "iam:ListRoleTags",
      "iam:PutRolePolicy",
      "iam:TagRole",
      "iam:UntagRole",
      "iam:UpdateAssumeRolePolicy",
      "iam:UpdateRole",
    ]

    resources = [
      local.dev_agentcore_runtime_execution_role_arn,
    ]
  }

  statement {
    sid     = "PassExactAgentCoreRuntimeExecutionRole"
    effect  = "Allow"
    actions = ["iam:PassRole"]

    resources = [
      local.dev_agentcore_runtime_execution_role_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["bedrock-agentcore.amazonaws.com"]
    }
  }

  statement {
    sid    = "CreateTaggedBoundedAgentCoreRuntime"
    effect = "Allow"

    actions = [
      "bedrock-agentcore:CreateAgentRuntime",
    ]

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
      variable = "aws:RequestTag/Purpose"
      values   = [local.dev_agentcore_runtime_purpose]
    }
  }

  statement {
    sid     = "CreateAgentCoreDefaultRuntimeEndpointDependency"
    effect  = "Allow"
    actions = ["bedrock-agentcore:CreateAgentRuntimeEndpoint"]

    resources = [
      local.dev_agentcore_runtime_precreation_arn,
    ]
  }

  statement {
    sid     = "TagAgentCoreRuntimeDuringCreateDependency"
    effect  = "Allow"
    actions = ["bedrock-agentcore:TagResource"]

    resources = [
      local.dev_agentcore_runtime_precreation_arn,
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
      variable = "aws:RequestTag/Purpose"
      values   = [local.dev_agentcore_runtime_purpose]
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
      test     = "ForAllValues:StringEquals"
      variable = "aws:TagKeys"
      values = [
        "Environment",
        "ManagedBy",
        "Project",
        "Purpose",
        "Repository",
      ]
    }
  }

  statement {
    sid     = "TagAgentCoreWorkloadIdentityDuringCreateDependency"
    effect  = "Allow"
    actions = ["bedrock-agentcore:TagResource"]

    resources = [
      local.dev_agentcore_workload_identity_directory_arn,
      local.dev_agentcore_workload_identity_precreation_arn,
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
      variable = "aws:RequestTag/Purpose"
      values   = [local.dev_agentcore_runtime_purpose]
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
      test     = "ForAllValues:StringEquals"
      variable = "aws:TagKeys"
      values = [
        "Environment",
        "ManagedBy",
        "Project",
        "Purpose",
        "Repository",
      ]
    }
  }

  statement {
    sid     = "CreateAgentCoreManagedWorkloadIdentityDependency"
    effect  = "Allow"
    actions = ["bedrock-agentcore:CreateWorkloadIdentity"]

    resources = [
      local.dev_agentcore_workload_identity_directory_arn,
      local.dev_agentcore_workload_identity_precreation_arn,
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
      variable = "aws:RequestTag/Purpose"
      values   = [local.dev_agentcore_runtime_purpose]
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
      test     = "ForAllValues:StringEquals"
      variable = "aws:TagKeys"
      values = [
        "Environment",
        "ManagedBy",
        "Project",
        "Purpose",
        "Repository",
      ]
    }
  }

  statement {
    sid    = "ManageExactBoundedAgentCoreRuntime"
    effect = "Allow"

    actions = [
      "bedrock-agentcore:DeleteAgentRuntime",
      "bedrock-agentcore:GetAgentRuntime",
      "bedrock-agentcore:ListTagsForResource",
      "bedrock-agentcore:TagResource",
      "bedrock-agentcore:UntagResource",
      "bedrock-agentcore:UpdateAgentRuntime",
    ]

    resources = [
      local.dev_agentcore_runtime_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/Project"
      values   = ["opslens"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/Environment"
      values   = ["dev"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/Purpose"
      values   = [local.dev_agentcore_runtime_purpose]
    }
  }

  statement {
    sid     = "DeleteExactAgentCoreDefaultRuntimeEndpointDependency"
    effect  = "Allow"
    actions = ["bedrock-agentcore:DeleteAgentRuntimeEndpoint"]

    resources = [
      local.dev_agentcore_runtime_arn,
      local.dev_agentcore_runtime_endpoint_arn,
    ]
  }

  statement {
    sid     = "DeleteAgentCoreGeneratedWorkloadIdentityDependency"
    effect  = "Allow"
    actions = ["bedrock-agentcore:DeleteWorkloadIdentity"]

    resources = [
      local.dev_agentcore_workload_identity_directory_arn,
      local.dev_agentcore_workload_identity_arn,
    ]
  }
}

resource "aws_iam_policy" "github_actions_agentcore_deploy" {
  name        = "OpsLensAgentCoreDeployDevAccess"
  description = "Allow main-only GitHub Actions to manage the bounded Phase 14 AgentCore experiment."

  policy = data.aws_iam_policy_document.github_actions_agentcore_deploy.json
}

resource "aws_iam_role_policy_attachment" "github_actions_agentcore_deploy" {
  role       = aws_iam_role.github_actions_deploy.name
  policy_arn = aws_iam_policy.github_actions_agentcore_deploy.arn
}
