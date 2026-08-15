locals {
  dev_epss_lambda_execution_role_name = "OpsLensEpssIngestionLambdaRole"
  dev_epss_lambda_execution_role_arn = (
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${local.dev_epss_lambda_execution_role_name}"
  )
}

data "aws_iam_policy_document" "github_actions_lambda_runtime_iam" {
  statement {
    sid    = "CreateEpssLambdaExecutionRole"
    effect = "Allow"

    actions = [
      "iam:CreateRole",
    ]

    resources = [
      local.dev_epss_lambda_execution_role_arn,
    ]
  }

  statement {
    sid    = "ManageEpssLambdaExecutionRole"
    effect = "Allow"

    actions = [
      "iam:DeleteRole",
      "iam:GetRole",
      "iam:GetRolePolicy",
      "iam:ListAttachedRolePolicies",
      "iam:ListInstanceProfilesForRole",
      "iam:ListRolePolicies",
      "iam:ListRoleTags",
      "iam:TagRole",
      "iam:UntagRole",
      "iam:UpdateAssumeRolePolicy",
    ]

    resources = [
      local.dev_epss_lambda_execution_role_arn,
    ]
  }

  statement {
    sid    = "ManageEpssLambdaExecutionRoleInlinePolicy"
    effect = "Allow"

    actions = [
      "iam:DeleteRolePolicy",
      "iam:PutRolePolicy",
    ]

    resources = [
      local.dev_epss_lambda_execution_role_arn,
    ]
  }
}

resource "aws_iam_role_policy" "github_actions_lambda_runtime_iam" {
  name = "OpsLensLambdaRuntimeIamDevAccess"
  role = aws_iam_role.github_actions_deploy.id

  policy = data.aws_iam_policy_document.github_actions_lambda_runtime_iam.json
}
